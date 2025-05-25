from collections import defaultdict
from contextlib import nullcontext
from dataclasses import dataclass, field
from functools import cached_property
import json
from typing import TYPE_CHECKING, Any, Callable, ClassVar, Iterable, Literal, Never, NotRequired, Self, TypedDict

import mariadb

from database import queries
from discordtools import feedbackerrors as fbe
from structures import attribute
from utils import metautils, parsetools, text

from database import strong as S
from database.strong import Tables as TBL

import pickle

from structures.user import User

from structures.attribute import AbstractAttribute, AnyAttributeT, AttributeValueTypeT, CollectionTreeItem, CollectionTreeT, StaticAttribute, TaskAttribute, AttributeValueType, UserAttribute
from structures.task import Task
from utils.locked import equality_locked

if TYPE_CHECKING:
    from structures.community import Community


# --- Collection Types --- #

class UserCollectionTreeItemT(TypedDict, total=True):
    value: str
    aliases: list[str]
    sort_value: int
    nodes: NotRequired[list['UserCollectionTreeItemT']]
type UserCollectionTreeT = list[UserCollectionTreeItemT]

type UserCollectionT = None | UserCollectionTreeT


@dataclass(frozen=True, kw_only=True)
class List:
    MAX_NAME_LENGTH: ClassVar[int] = 64
    MAX_ATTRIBUTES: ClassVar[int] = 2
    MAX_TASKS: ClassVar[int] = 1

    INVALID_ENDING: ClassVar[str] = __name__.lower()

    community: 'Community'
    id: int
    name: str
    
    @property
    def identity(self) -> tuple[int, ...]:
        return (self.id,) + self.community.identity

    def __hash__(self) -> int:
        return hash(self.identity)
    
    def __eq__(self, value: object) -> bool:
        return isinstance(value, self.__class__) and self.identity == value.identity
    

    # --- Handle User Collection ---

    def handle_user_collection(
        self,
        bad_collection: str, 
        attribute: TaskAttribute | UserAttribute,
    ) -> None:
        user_collection: UserCollectionT = parsetools.json_loads_safe(
            bad_collection, 
            AbstractAttribute.COLLECTION_MAX_DEPTH
        )

        if not user_collection:
            return
        
        if not isinstance(user_collection, list):
            raise fbe.TemporaryFeedbackError("Not a tree")
        
        unique_flattened = self._recursively_parse_validate_flatten_user_collection(user_collection, attribute.value_type)

        self._insert_collection_into_db(unique_flattened, attribute)

    def _recursively_parse_validate_flatten_user_collection[T: AttributeValueTypeT](
        self,
        user_collection_tree: UserCollectionTreeT, 
        value_type: AttributeValueType[T]
    ) -> list[CollectionTreeItem[T]]:
        flattened: list[CollectionTreeItem[T]] = []
        seen: set[T] = set()

        def recursive(tree: UserCollectionTreeT) -> CollectionTreeT[T]:
            result: CollectionTreeT[T] = []

            for item in tree:
                value, aliases, sort_value = self._extract_data_from_collection_item(item, value_type)

                for syn in (value, *aliases):
                    normed = attribute._normalize_collection_value(syn)

                    if normed in seen:
                        raise fbe.TemporaryFeedbackError(f"The value or alias `{normed}` appeared more than once in the collection.")
                    
                    seen.add(normed)

                nodes = item.get('nodes', [])

                if not isinstance(nodes, list):
                    raise fbe.TemporaryFeedbackError("Not a sub tree")
                
                item = CollectionTreeItem(
                    value,
                    aliases,
                    sort_value,
                    recursive(nodes)
                )

                for node in item.nodes:
                    node.root = item

                result.append(item)
                flattened.append(item)

            return result
            
        recursive(user_collection_tree)

        return flattened

    def _extract_data_from_collection_item[T: AttributeValueTypeT](
        self,
        item: UserCollectionTreeItemT,
        value_type: AttributeValueType[T]
    ) -> tuple[T, set[T], int]:
        try:
            sort_value: int = int(item['sort_value'])
        except KeyError as e:
            raise fbe.TemporaryFeedbackError(f"Missing {e.args[0]}")
        except ValueError as e:
            raise fbe.TemporaryFeedbackError("Not an int", item['sort_value'])
            
        AbstractAttribute.any_number_valid(sort_value)

        try:
            bad_value = item['value']
        except KeyError as e:
            raise fbe.TemporaryFeedbackError(f"Missing {e.args[0]}")
        
        try:
            bad_aliases = item.get('aliases', [])

            if not isinstance(bad_aliases, list):
                raise TypeError()
        except TypeError:
            raise fbe.TemporaryFeedbackError(f"Not a list of aliases")
        
        value: T = AbstractAttribute.from_str_singular(bad_value, value_type)

        bad_aliases = set(bad_aliases)
        aliases: set[T] = {AbstractAttribute.from_str_singular(alias, value_type) for alias in bad_aliases}

        return (value, aliases, sort_value)

    def _insert_collection_into_db[T: AttributeValueTypeT](
        self, 
        unique_flattened: list[CollectionTreeItem[T]], 
        attribute: TaskAttribute | UserAttribute
    ) -> None:
        if isinstance(attribute, TaskAttribute):
            AttrCollTable = TBL.TaskAttributeCollectionNode
            AttrCollAliasTable = TBL.TaskAttributeCollectionNodeAlias
        elif isinstance(attribute, UserAttribute):
            AttrCollTable = TBL.UserAttributeCollectionNode
            AttrCollAliasTable = TBL.UserAttributeCollectionNodeAlias
        else:
            raise RuntimeError()
        
        h = queries.ArgHelper()
        value_to_id: dict[T, int] = {}

        with equality_locked(self), queries.connected() as (conn, cursor):
            # Insert all nodes, roots are NULL for now and map value to ids
            for item in unique_flattened:
                cursor.execute(f"""
                    INSERT INTO {AttrCollTable} (
                        {AttrCollTable.root_id},
                        {AttrCollTable._attribute_id},
                        {AttrCollTable.value},
                        {AttrCollTable.sort_value}
                    )
                    VALUES 
                    (
                        {h|None},
                        {h|attribute.id},
                        {h|pickle.dumps(item.value)},
                        {h|item.sort_value}
                    )
                """, h.steal())

                item_id: int = cursor.lastrowid  # type: ignore
                value_to_id[item.value] = item_id

            # Now that ids are known, insert the roots and insert aliases
            for item in unique_flattened:
                item_id = value_to_id[item.value]

                if item.root is not None:
                    root_id = value_to_id[item.root.value]

                    cursor.execute(f"""
                        UPDATE {AttrCollTable}
                        SET {AttrCollTable.root_id} = {h|root_id}
                        WHERE {AttrCollTable.id} = {h|item_id}
                    """, h.steal())

                cursor.execute(f"""
                    INSERT INTO {AttrCollAliasTable} (
                        {AttrCollAliasTable._attribute_collection_node_id},
                        {AttrCollAliasTable.alias}
                    )
                    VALUES 
                        {','.join(f"({h|item_id}, {h|alias})" for alias in item.aliases)}
                """, h.steal()) 
    

    # --- All Attributes ---
    
    def delete_attribute(self, bad_name: str) -> None:
        static_attribute = self.get_static_attribute_by_name(text.sanitize(bad_name))

        if static_attribute is not None:
            return self.delete_static_attribute()

        self._generic_delete_attribute(None, bad_name)
        
    def get_attributes(self, where: Callable[[queries.ArgHelper], str] | None = None) -> list[AnyAttributeT]:
        return self.get_static_attributes(where) + self.get_task_attributes(where) + self.get_user_attributes(where)

    def get_attribute_by_name(self, name: str) -> AnyAttributeT | None:
        return (
            self.get_static_attribute_by_name(name)
            or self.get_task_attribute_by_name(name)
            or self.get_user_attribute_by_name(name)
        )
        
    def get_attribute_by_alias(self, alias: str) -> AnyAttributeT | None:
        return (
            self.get_static_attribute_by_alias(alias)
            or self.get_task_attribute_by_alias(alias)
            or self.get_user_attribute_by_alias(alias)
        )

    def get_attribute_by_syn(self, syn: str) -> AnyAttributeT | None:
        return (
            self.get_static_attribute_by_syn(syn)
            or self.get_task_attribute_by_syn(syn)
            or self.get_user_attribute_by_syn(syn)
        )

    def _generic_create_attribute(
        self,
        bad_name: str,
        bad_aliases: Iterable[str],
        max_slots: int,
        min_slots: int = 0
    ) -> tuple[str, set[str], int]:
        with equality_locked(self):
            name, aliases = text.validate_and_sanitize_syns(
                bad_name, 
                bad_aliases, 
                StaticAttribute.MAX_SYN_LEN, 
                StaticAttribute.MAX_ALIAS_COUNT + 1, 
                ()
            )

            attributes = self.get_attributes()

            if len(attributes) >= self.__class__.MAX_ATTRIBUTES:
                raise fbe.TemporaryFeedbackError("Max attributes reached")

            if self.get_attribute_by_name(name) is not None:
                raise fbe.TemporaryFeedbackError(f"Attribute name `{name}` already used as name or alias of different attribute")
            
            for alias in aliases:
                if self.get_attribute_by_alias(alias) is not None:
                    raise fbe.TemporaryFeedbackError(f"Attribute alias `{alias}` already used as name or alias of different attribute")

            if not (1 <= max_slots <= AbstractAttribute.MAX_SLOTS):
                raise fbe.TemporaryFeedbackError()

            if not (0 <= min_slots <= max_slots):
                raise fbe.TemporaryFeedbackError()
            
            index = max(attr.index for attr in attributes) + 1 if attributes else 1

            return (name, aliases, index)
        
    def _generic_delete_attribute(self, attribute_type: type[AnyAttributeT] | None, bad_name: str) -> None:
        from database import dbutils

        name = text.sanitize(bad_name)

        h = queries.ArgHelper()

        with equality_locked(self), queries.connected() as (conn, cursor):
            if attribute_type is None:
                attribute = self.get_attribute_by_name(name)

                if attribute is None:
                    raise fbe.TemporaryFeedbackError("No attribute with that name found")
                
                attribute_type = type(attribute)
                
            Tbl = dbutils.get_attribute_table(attribute_type)

            cursor.execute(f"""
                DELETE FROM {Tbl}
                WHERE 
                    {Tbl.list_id} = {h|self.id}
                    AND {Tbl.name} = {h|name}
            """, h.steal())

            # For when attribute_type is given, otherwise this should always be != 0
            affected: int = cursor.rowcount

            if affected == 0:
                raise fbe.TemporaryFeedbackError("No attribute with that name found")


    # --- Static Attribute ---

    def create_static_attribute[T: AttributeValueTypeT](
        self,
        bad_name: str,
        bad_aliases: Iterable[str],
        value_type: AttributeValueType[T],
        min_slots: int,
        max_slots: int,
        unique_slots: bool,
        unique_value_per_list: bool
    ) -> StaticAttribute[T]:
        """This method should not public to the user!"""
        with equality_locked(self):
            assert self.get_tasks() == []
            
            name, aliases, index = self._generic_create_attribute(bad_name, bad_aliases, max_slots, min_slots)

            h = queries.ArgHelper()
            SAT = TBL.StaticAttribute

            with queries.connected() as (conn, cursor):
                cursor.execute(f"""
                    INSERT INTO {SAT} (
                        {SAT.list_id},
                        {SAT.name},
                        {SAT.value_type},
                        {SAT.index},
                        {SAT.min_slots},
                        {SAT.max_slots},
                        {SAT.unique_slots},
                        {SAT.unique_value_per_list}
                    )
                    VALUES (
                        {h|self.id},
                        {h|name},
                        {h|value_type.id},
                        {h|index},
                        {h|min_slots},
                        {h|max_slots},
                        {h|unique_slots},
                        {h|unique_value_per_list}
                    )
                """, h.steal())

                attribute_id: int = cursor.lastrowid  # type: ignore

                SAAT = TBL.StaticAttributeAlias

                if aliases:
                    cursor.execute(f"""
                        INSERT INTO {SAAT} (
                            {SAAT.static_attribute_id},
                            {SAAT.list_id},
                            {SAAT.alias}
                        ) 
                        VALUES 
                            {','.join(f"({h|attribute_id}, {h|self.id}, {h|alias})" for alias in aliases)}
                    """, h.steal())

                obj = StaticAttribute(
                    list=self,
                    id=attribute_id,
                    name=name,
                    value_type=value_type,
                    index=index,
                    min_slots=0,
                    max_slots=max_slots,
                    unique_slots=unique_slots,
                    unique_value_per_list=unique_value_per_list
                )

                return obj
            
    def delete_static_attribute(self) -> Never:
        raise fbe.TemporaryFeedbackError("Static attribute cannot be deleted!")

    def _fetch_static_attributes_from_table(self, where: Callable[[queries.ArgHelper], str] | None) -> S.ManyTableRowT:
        h = queries.ArgHelper()
        
        with queries.connected() as (conn, cursor):
            cursor.execute(f"""
                SELECT *
                FROM {TBL.StaticAttribute}
                WHERE 
                    {TBL.StaticAttribute.list_id} = {h|self.id}
                    {f"AND {where(h)}" if where is not None else ""}
            """, h.steal())

            result: S.ManyTableRowT = cursor.fetchall()

        return result
    
    def _static_attribute_data_to_obj(self, data: S.SingleTableRowT) -> StaticAttribute:
        SAT = TBL.StaticAttribute

        return StaticAttribute(
            list=self,
            id=data[SAT.id],
            name=data[SAT.name],
            value_type=AttributeValueType.get_by_id(data[SAT.value_type]),
            index=data[SAT.index],
            min_slots=data[SAT.min_slots],
            max_slots=data[SAT.max_slots],
            unique_slots=data[SAT.unique_slots],
            unique_value_per_list=data[SAT.unique_value_per_list]
        )
    
    def get_static_attributes(self, where: Callable[[queries.ArgHelper], str] | None = None) -> list[StaticAttribute]:
        return [
            self._static_attribute_data_to_obj(data) 
            for data in self._fetch_static_attributes_from_table(where)
        ]

    def get_static_attribute_by_id(self, id: int) -> StaticAttribute | None:
        data = self._fetch_static_attributes_from_table(lambda h: f"{TBL.StaticAttribute.id} = {h|id}")
        return self._static_attribute_data_to_obj(data[0]) if data else None
    
    def get_static_attribute_by_name(self, name: str) -> StaticAttribute | None:
        data = self._fetch_static_attributes_from_table(lambda h: f"{TBL.StaticAttribute.name} = {h|name}")
        return self._static_attribute_data_to_obj(data[0]) if data else None

    def get_static_attribute_by_alias(self, alias: str) -> StaticAttribute | None:
        h = queries.ArgHelper()
        SAAT = TBL.StaticAttributeAlias

        with queries.connected() as (conn, cursor):
            cursor.execute(f"""
                SELECT {SAAT.static_attribute_id}
                FROM {SAAT}
                WHERE
                    {SAAT.list_id} = {h|self.id}
                    AND {SAAT.alias} = {h|alias}
            """, h.steal())

            result: S.SingleTableRowT | None = cursor.fetchone()

        if result is None:
            return None
        
        return self.get_static_attribute_by_id(result[SAAT.static_attribute_id])
    
    def get_static_attribute_by_syn(self, syn: str) -> StaticAttribute | None:
        return (
            self.get_static_attribute_by_name(syn)
            or self.get_static_attribute_by_alias(syn)
        )
    
    def get_static_name_attribute(self) -> StaticAttribute[str]:
        name_attribute = self.get_static_attribute_by_name(Task.STATIC_NAME_ATTRIBUTE_NAME)
        assert name_attribute is not None
        return name_attribute
    
    def get_static_alias_attribute(self) -> StaticAttribute[str]:
        alias_attribute = self.get_static_attribute_by_name(Task.STATIC_ALIAS_ATTRIBUTE_NAME)
        assert alias_attribute is not None
        return alias_attribute

    # --- Task Attributes ---
    
    def create_task_attribute[T: AttributeValueTypeT](
        self,
        bad_name: str,
        bad_aliases: Iterable[str],
        value_type: AttributeValueType[T],
        bad_collection: str,
        min_slots: int,
        max_slots: int,
        unique_slots: bool,
        unique_value_per_list: bool
    ) -> TaskAttribute[T]:
        with equality_locked(self):
            name, aliases, index = self._generic_create_attribute(bad_name, bad_aliases, min_slots)

            h = queries.ArgHelper()
            SAT = TBL.TaskAttribute

            with queries.connected() as (conn, cursor):
                cursor.execute(f"""
                    INSERT INTO {SAT} (
                        {SAT.list_id},
                        {SAT.name},
                        {SAT.value_type},
                        {SAT.index},
                        {SAT.min_slots},
                        {SAT.max_slots},
                        {SAT.unique_slots},
                        {SAT.unique_value_per_list}
                    )
                    VALUES (
                        {h|self.id},
                        {h|name},
                        {h|value_type.id},
                        {h|index},
                        {h|min_slots},
                        {h|max_slots},
                        {h|unique_slots},
                        {h|unique_value_per_list}
                    )
                """, h.steal())

                attribute_id: int = cursor.lastrowid  # type: ignore

                TAAT = TBL.TaskAttributeAlias

                cursor.execute(f"""
                    INSERT INTO {TAAT} (
                        {TAAT.task_attribute_id},
                        {TAAT.list_id},
                        {TAAT.alias}
                    ) 
                    VALUES 
                        {','.join(f"({h|attribute_id}, {h|self.id}, {h|alias})" for alias in aliases)}
                    )
                """, h.steal())

                obj = TaskAttribute(
                    list=self,
                    id=attribute_id,
                    name=name,
                    value_type=value_type,
                    index=index,
                    min_slots=min_slots,
                    max_slots=max_slots,
                    unique_slots=unique_slots,
                    unique_value_per_list=unique_value_per_list
                )

                self.handle_user_collection(bad_collection, obj)

                return obj
    
    def delete_task_attribute(self, bad_name: str) -> None:
        self._generic_delete_attribute(TaskAttribute, bad_name)
            
    def _fetch_task_attributes_from_table(self, where: Callable[[queries.ArgHelper], str] | None) -> S.ManyTableRowT:
        h = queries.ArgHelper()
        
        with queries.connected() as (conn, cursor):
            cursor.execute(f"""
                SELECT *
                FROM {TBL.TaskAttribute}
                WHERE 
                    {TBL.TaskAttribute.list_id} = {h|self.id}
                    {f"AND {where(h)}" if where is not None else ""}
            """, h.steal())

            result: S.ManyTableRowT = cursor.fetchall()

        return result
    
    def _task_attribute_data_to_obj(self, data: S.SingleTableRowT) -> TaskAttribute:
        TAT = TBL.TaskAttribute

        return TaskAttribute(
            list=self,
            id=data[TAT.id],
            name=data[TAT.name],
            index=data[TAT.index],
            value_type=AttributeValueType.get_by_id(data[TAT.value_type]),
            min_slots=data[TAT.min_slots],
            max_slots=data[TAT.max_slots],
            unique_slots=data[TAT.unique_slots],
            unique_value_per_list=data[TAT.unique_value_per_list]
        )
    
    def get_task_attributes(self, where: Callable[[queries.ArgHelper], str] | None = None) -> list[TaskAttribute]:
        return [
            self._task_attribute_data_to_obj(data) 
            for data in self._fetch_task_attributes_from_table(where)
        ]

    def get_task_attribute_by_id(self, id: int) -> TaskAttribute | None:
        data = self._fetch_task_attributes_from_table(lambda h: f"{TBL.TaskAttribute.id} = {h|id}")
        return self._task_attribute_data_to_obj(data[0]) if data else None
    
    def get_task_attribute_by_name(self, name: str) -> TaskAttribute | None:
        data = self._fetch_task_attributes_from_table(lambda h: f"{TBL.TaskAttribute.name} = {h|name}")
        return self._task_attribute_data_to_obj(data[0]) if data else None
    
    def get_task_attribute_by_alias(self, alias: str) -> TaskAttribute | None:
        h = queries.ArgHelper()

        with queries.connected() as (conn, cursor):
            cursor.execute(f"""
                SELECT {TBL.TaskAttributeAlias.task_attribute_id}
                FROM {TBL.TaskAttributeAlias}
                WHERE
                    {TBL.TaskAttributeAlias.list_id} = {h|self.id}
                    AND {TBL.TaskAttributeAlias.alias} = {h|alias}
            """, h.steal())

            result: S.SingleTableRowT | None = cursor.fetchone()

        if result is None:
            return None
        
        return self.get_task_attribute_by_id(result[TBL.TaskAttributeAlias.task_attribute_id])

    def get_task_attribute_by_syn(self, syn: str) -> TaskAttribute | None:
        return (
            self.get_task_attribute_by_name(syn)
            or self.get_task_attribute_by_alias(syn)
        )
    

    # --- User Attributes ---

    def create_user_attribute[T: AttributeValueTypeT](
        self,
        bad_name: str,
        bad_aliases: Iterable[str],
        value_type: AttributeValueType[T],
        bad_collection: str,
        min_slots: int,
        max_slots: int,
        unique_slots: bool
    ) -> UserAttribute[T]:
        with equality_locked(self):
            name, aliases, index = self._generic_create_attribute(bad_name, bad_aliases, max_slots)

            h = queries.ArgHelper()
            UAT = TBL.UserAttribute

            with queries.connected() as (conn, cursor):
                cursor.execute(f"""
                    INSERT INTO {UAT} (
                        {UAT.list_id},
                        {UAT.name},
                        {UAT.value_type},
                        {UAT.index},
                        {UAT.min_slots},
                        {UAT.max_slots},
                        {UAT.unique_slots}
                    )
                    VALUES (
                        {h|self.id},
                        {h|name},
                        {h|value_type.id},
                        {h|index},
                        {h|min_slots},
                        {h|max_slots},
                        {h|unique_slots}
                    )
                """, h.steal())

                attribute_id: int = cursor.lastrowid  # type: ignore

                UAAT = TBL.UserAttributeAlias

                cursor.execute(f"""
                    INSERT INTO {UAAT} (
                        {UAAT.user_attribute_id},
                        {UAAT.list_id},
                        {UAAT.alias}
                    ) 
                    VALUES 
                        {','.join(f"({h|attribute_id}, {h|self.id}, {h|alias})" for alias in aliases)}
                    )
                """, h.steal())

                obj = UserAttribute(
                    list=self,
                    id=attribute_id,
                    name=name,
                    value_type=value_type,
                    index=index,
                    min_slots=min_slots,
                    max_slots=max_slots,
                    unique_slots=unique_slots
                )

                self.handle_user_collection(bad_collection, obj)

                return obj
    
    def delete_user_attribute(self, bad_name: str) -> None:
        self._generic_delete_attribute(UserAttribute, bad_name)

    def _fetch_user_attributes_from_table(self, where: Callable[[queries.ArgHelper], str] | None) -> S.ManyTableRowT:
        h = queries.ArgHelper()
        
        with queries.connected() as (conn, cursor):
            cursor.execute(f"""
                SELECT *
                FROM {TBL.UserAttribute}
                WHERE 
                    {TBL.UserAttribute.list_id} = {h|self.id}
                    {f"AND {where(h)}" if where is not None else ""}
            """, h.steal())

            result: S.ManyTableRowT = cursor.fetchall()

        return result
    
    def _user_attribute_data_to_obj(self, data: S.SingleTableRowT) -> UserAttribute:
        UAT = TBL.UserAttribute

        return UserAttribute(
            list=self,
            id=data[UAT.id],
            name=data[UAT.name],
            index=data[UAT.index],
            value_type=AttributeValueType.get_by_id(data[UAT.value_type]),
            min_slots=data[UAT.min_slots],
            max_slots=data[UAT.max_slots],
            unique_slots=data[UAT.unique_slots]
        )
    
    def get_user_attributes(self, where: Callable[[queries.ArgHelper], str] | None = None) -> list[UserAttribute]:
        return [
            self._user_attribute_data_to_obj(data) 
            for data in self._fetch_user_attributes_from_table(where)
        ]

    def get_user_attribute_by_id(self, id: int) -> UserAttribute | None:
        data = self._fetch_user_attributes_from_table(lambda h: f"{TBL.UserAttribute.id} = {h|id}")
        return self._user_attribute_data_to_obj(data[0]) if data else None
    
    def get_user_attribute_by_name(self, name: str) -> UserAttribute | None:
        data = self._fetch_user_attributes_from_table(lambda h: f"{TBL.UserAttribute.name} = {h|name}")
        return self._user_attribute_data_to_obj(data[0]) if data else None
    
    def get_user_attribute_by_alias(self, alias: str) -> UserAttribute | None:
        h = queries.ArgHelper()

        with queries.connected() as (conn, cursor):
            cursor.execute(f"""
                SELECT {TBL.UserAttributeAlias.user_attribute_id}
                FROM {TBL.UserAttributeAlias}
                WHERE
                    {TBL.UserAttributeAlias.list_id} = {h|self.id}
                    AND {TBL.UserAttributeAlias.alias} = {h|alias}
            """, h.steal())

            result: S.SingleTableRowT | None = cursor.fetchone()
        
        if result is None:
            return None
        
        return self.get_user_attribute_by_id(result[TBL.UserAttributeAlias.user_attribute_id])

    def get_user_attribute_by_syn(self, syn: str) -> UserAttribute | None:
        return (
            self.get_user_attribute_by_name(syn)
            or self.get_user_attribute_by_alias(syn)
        )


    # --- Tasks ---

    def create_task(self, bad_name: str, bad_aliases: Iterable[str], **kwargs: str) -> 'Task':
        with equality_locked(self):
            name, aliases = text.validate_and_sanitize_syns(
                bad_name, 
                bad_aliases, 
                Task.MAX_SYN_LEN,
                self.get_static_alias_attribute().max_slots
            )

            h = queries.ArgHelper()

            with queries.connected() as (conn, cursor):
                cursor.execute(f"""
                    INSERT INTO {TBL.Task} (
                        {TBL.Task.list_id},
                        {TBL.Task.name}
                    )
                    VALUES (
                        {h|self.id},
                        {h|name}
                    )
                """, h.steal())

                task_id: int = cursor.lastrowid  # type: ignore

                cursor.execute(f"""
                    INSERT INTO {TBL.TaskAlias} (
                        {TBL.TaskAlias.task_id},
                        {TBL.TaskAlias.list_id},
                        {TBL.TaskAlias.alias}
                    ) 
                    VALUES 
                        {','.join(f"({h|task_id}, {h|self.id}, {h|alias})" for alias in aliases)}        
                    
                """, h.steal())

            return Task(
                list=self,
                id=task_id,
                name=name
            )
        
    def _fetch_tasks_from_table(self, where: Callable[[queries.ArgHelper], str] | None) -> S.ManyTableRowT:
        h = queries.ArgHelper()
        
        with queries.connected() as (conn, cursor):
            cursor.execute(f"""
                SELECT *
                FROM {TBL.Task}
                WHERE 
                    {TBL.Task.list_id} = {h|self.id}
                    {f"AND {where(h)}" if where is not None else ""}
            """, h.steal())

            result: S.ManyTableRowT = cursor.fetchall()

        return result
    
    def _task_data_to_obj(self, data: S.SingleTableRowT) -> Task:
        return Task(
            list=self,
            id=data[TBL.Task.id],
            name=data[TBL.Task.name]
        )
    
    def get_tasks(self, where: Callable[[queries.ArgHelper], str] | None = None) -> list[Task]:
        return [
            self._task_data_to_obj(data) 
            for data in self._fetch_tasks_from_table(where)
        ]

    def get_task_by_id(self, id: int) -> Task | None:
        data = self._fetch_tasks_from_table(lambda h: f"{TBL.Task.id} = {h|id}")
        return self._task_data_to_obj(data[0]) if data else None
    
    def get_task_by_name(self, name: str) -> Task | None:
        data = self._fetch_tasks_from_table(lambda h: f"{TBL.Task.name} = {h|name}")
        return self._task_data_to_obj(data[0]) if data else None

    def get_task_by_alias(self, alias: str) -> Task | None:
        alias = text.sanitize(alias)
        h = queries.ArgHelper()

        with queries.connected() as (conn, cursor):
            cursor.execute(f"""
                SELECT {TBL.TaskAlias.task_id}
                FROM {TBL.TaskAlias}
                WHERE 
                    {TBL.TaskAlias.list_id} = {h|self.id}
                    AND {TBL.TaskAlias.alias} = {h|alias}
            """, h.steal())

            result: S.SingleTableRowT | None = cursor.fetchone()

        if result is None:
            return None
        
        return self.get_task_by_id(result[TBL.TaskAlias.task_id])