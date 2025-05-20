from collections import defaultdict
from contextlib import nullcontext
from dataclasses import dataclass, field
from functools import cached_property
import json
from typing import TYPE_CHECKING, Any, Callable, ClassVar, Iterable, Literal, NotRequired, Self, TypedDict

import mariadb

from database import queries
from discordtools import feedbackerrors as fbe
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
    MAX_ATTRIBUTES: ClassVar[int] = 1
    MAX_TASKS: ClassVar[int] = 1

    INVALID_ENDING: ClassVar[str] = __name__.lower()

    community: 'Community'
    id: int
    name: str

    @property
    def name_attribute(self) -> StaticAttribute[str]:
        return StaticAttribute(
            list=self,
            id=0,
            name='name',
            value_type=AttributeValueType.get_by_type(str),
            index=1,
            get_collection=[],
            min_slots=1,
            max_slots=1,
            unique_slots=False,
            get_value=lambda task: [task.name]
        )
    
    @property
    def alias_attribute(self) -> StaticAttribute[str]:
        return StaticAttribute(
            list=self,
            id=0,
            name='alias',
            value_type=AttributeValueType.get_by_type(str),
            index=2,
            get_collection=[],
            min_slots=0,
            max_slots=StaticAttribute.MAX_SLOTS,
            unique_slots=True,
            get_value=lambda task: sorted(task.aliases)
        )
    
    @property
    def identity(self) -> tuple[int, ...]:
        return (self.id,) + self.community.identity

    def __hash__(self) -> int:
        return hash(self.identity)
    
    def __eq__(self, value: object) -> bool:
        return isinstance(value, self.__class__) and self.identity == value.identity
        


    # --- All Attributes ---

    def on_attribute_created(self, attribute: AnyAttributeT, default_value: str | None) -> None:
        ...

    
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
        min_slots: int,
        max_slots: int,
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
    
    def _handle_user_collection(
        self,
        bad_collection: str, 
        attribute: TaskAttribute | UserAttribute,
    ) -> None:
        user_value_collection: UserCollectionT = parsetools.json_loads_safe(
            bad_collection, 
            AbstractAttribute.COLLECTION_MAX_DEPTH
        )

        if not user_value_collection:
            return
        
        if not isinstance(user_value_collection, list):
            raise fbe.TemporaryFeedbackError("Not a tree")
        
        flattened = self._parse_and_get_flattened_user_collection_tree(user_value_collection, attribute.value_type)

        self._insert_flattened_collection_data_into_db(flattened, attribute)

    def _parse_and_get_flattened_user_collection_tree[T: AttributeValueTypeT](
        self,
        user_collection_tree: UserCollectionTreeT, 
        value_type: AttributeValueType[T]
    ) -> CollectionTreeT[T]:
        lookup: dict[T, CollectionTreeItem[T]] = {}

        def recursive(tree: UserCollectionTreeT) -> CollectionTreeT[T]:
            result: CollectionTreeT[T] = []

            for item in tree:
                value, aliases, sort_value = self._extract_data_from_collection_item(item, value_type)

                for syn in (value, *aliases):
                    if norm  
                        # TODO then raise error 


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

            return result
            
        recursive(user_collection_tree)

        return list(lookup.values())

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

    def _insert_flattened_collection_data_into_db[T: AttributeValueTypeT](
        self, 
        flat: CollectionTreeT[T], 
        attribute: TaskAttribute | UserAttribute
    ) -> None:
        if isinstance(attribute, TaskAttribute):
            ACNT = TBL.TaskAttributeCollectionNode
            ACNAT = TBL.TaskAttributeCollectionNodeAlias
            ACNTAttributeId = ACNT.task_attribute_id
            ACNATNodeId = ACNAT.task_attribute_collection_node_id
        elif isinstance(attribute, UserAttribute):
            ACNT = TBL.UserAttributeCollectionNode
            ACNAT = TBL.UserAttributeCollectionNodeAlias
            ACNTAttributeId = ACNT.user_attribute_id
            ACNATNodeId = ACNAT.user_attribute_collection_node_id
        else:
            raise RuntimeError()
        
        h = queries.ArgHelper()
        
        with equality_locked(self), queries.connected() as (conn, cursor):
            cursor.execute(f"""
                INSERT INTO {ACNT} (
                    {ACNT.root_id},
                    {ACNTAttributeId},
                    {ACNT.value},
                    {ACNT.sort_value}
                )
                VALUES (
                    
                )
            """)

    

        # --- Static Attribute ---

        def create_static_attribute[T: AttributeValueTypeT](
            self,
            bad_name: str,
            bad_aliases: Iterable[str],
            value_type: AttributeValueType[T],
            min_slots: int,
            max_slots: int,
            unique_slots: bool,
            unique_value_per_list: bool,
            default_value: str | None
        ) -> StaticAttribute:
            """This method should not public to the user!"""
            with equality_locked(self):
                name, aliases, index = self._generic_create_attribute(bad_name, bad_aliases, min_slots, max_slots)

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

                    cursor.execute(f"""
                        INSERT INTO {SAAT} (
                            {SAAT.static_attribute_id},
                            {SAAT.list_id},
                            {SAAT.alias}
                        ) 
                        VALUES 
                            {','.join(f"({h|attribute_id}, {h|self.id}, {h|alias})" for alias in aliases)}
                        )
                    """, h.steal())

                    obj = StaticAttribute(
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

                    self.on_attribute_created(obj, default_value)

                    return obj
        

    def _fetch_static_attributes_from_table(self, where: Callable[[queries.ArgHelper], str] | None) -> list[S.TableResultT]:
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
    
    def get_static_attributes(self, where: Callable[[queries.ArgHelper], str] | None) -> list[StaticAttribute]:
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
        unique_value_per_list: bool,
        default_value: str | None
    ) -> TaskAttribute:
        """This method should not public to the user!"""
        with equality_locked(self):
            name, aliases, index = self._generic_create_attribute(bad_name, bad_aliases, min_slots, max_slots)

            h = queries.ArgHelper()
            TAT = TBL.TaskAttribute

            with queries.connected() as (conn, cursor):
                cursor.execute(f"""
                    INSERT INTO {TAT} (
                        {TAT.list_id},
                        {TAT.name},
                        {TAT.value_type},
                        {TAT.index},
                        {TAT.min_slots},
                        {TAT.max_slots},
                        {TAT.unique_slots},
                        {TAT.unique_value_per_list}
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

                self.on_attribute_created(obj, default_value)

                return obj
            
    def _fetch_task_attributes_from_table(self, where: Callable[[queries.ArgHelper], str] | None) -> list[TaskAttributeResultT]:
        h = queries.ArgHelper()
        
        with queries.connected() as (conn, cursor):
            cursor.execute(f"""
                SELECT *
                FROM task_attribute
                WHERE 
                    list_id = {h|self.id}
                    {f"AND {where(h)}" if where is not None else ""}
            """, h.steal())

            result: list[TaskAttributeResultT] = cursor.fetchall()

        return result
    
    def _task_attribute_data_to_obj(self, data: TaskAttributeResultT) -> TaskAttribute:
        return TaskAttribute(
            list=self,
            id=data['id'],
            name=data['name'],
            index=data['index'],
            value_type=AttributeValueType.get_by_id(data['value_type']),
            get_collection=pickle.loads(data['collection']),
            min_slots=data['min_slots'],
            max_slots=data['max_slots'],
            unique_slots=data['unique_slots'],
            unique_value_per_list=data['unique_value_per_list']
        )
    
    def get_task_attributes(self, where: Callable[[queries.ArgHelper], str] | None = None) -> list[TaskAttribute]:
        return [
            self._task_attribute_data_to_obj(data) 
            for data in self._fetch_task_attributes_from_table(where)
        ]

    def get_task_attribute_by_id(self, id: int) -> TaskAttribute | None:
        data = self._fetch_task_attributes_from_table(lambda h: f"id = {h|id}")
        return self._task_attribute_data_to_obj(data[0]) if data else None
    
    def get_task_attribute_by_name(self, name: str) -> TaskAttribute | None:
        data = self._fetch_task_attributes_from_table(lambda h: f"name = {h|name}")
        return self._task_attribute_data_to_obj(data[0]) if data else None
    
    def get_task_attribute_by_alias(self, alias: str) -> TaskAttribute | None:
        h = queries.ArgHelper()

        with queries.connected() as (conn, cursor):
            cursor.execute(f"""
                SELECT task_attribute_id
                FROM task_attribute_alias
                WHERE
                    list_id = {h|self.id}
                    AND alias = {h|alias}
            """, h.steal())

            result: S.SingleTableRowT = cursor.fetchone()

        if result is None:
            return None
        
        return self.get_task_attribute_by_id(result['task_attribute_id'])

    def get_task_attribute_by_syn(self, syn: str) -> TaskAttribute | None:
        return (
            self.get_task_attribute_by_name(syn)
            or self.get_task_attribute_by_alias(syn)
        )


    # --- User Attributes ---

    def _fetch_user_attributes_from_table(self, where: Callable[[queries.ArgHelper], str] | None) -> list[UserAttributeResultT]:
        h = queries.ArgHelper()
        
        with queries.connected() as (conn, cursor):
            cursor.execute(f"""
                SELECT *
                FROM user_attribute
                WHERE 
                    list_id = {h|self.id}
                    {f"AND {where(h)}" if where is not None else ""}
            """, h.steal())

            result: list[UserAttributeResultT] = cursor.fetchall()

        return result
    
    def _user_attribute_data_to_obj(self, data: UserAttributeResultT) -> UserAttribute:
        return UserAttribute(
            list=self,
            id=data['id'],
            name=data['name'],
            index=data['index'],
            value_type=AttributeValueType.get_by_id(data['value_type']),
            get_collection=pickle.loads(data['collection']),
            min_slots=data['min_slots'],
            max_slots=data['max_slots'],
            unique_slots=data['unique_slots']
        )
    
    def get_user_attributes(self, where: Callable[[queries.ArgHelper], str] | None = None) -> list[UserAttribute]:
        return [
            self._user_attribute_data_to_obj(data) 
            for data in self._fetch_user_attributes_from_table(where)
        ]

    def get_user_attribute_by_id(self, id: int) -> UserAttribute | None:
        data = self._fetch_user_attributes_from_table(lambda h: f"id = {h|id}")
        return self._user_attribute_data_to_obj(data[0]) if data else None
    
    def get_user_attribute_by_name(self, name: str) -> UserAttribute | None:
        data = self._fetch_user_attributes_from_table(lambda h: f"name = {h|name}")
        return self._user_attribute_data_to_obj(data[0]) if data else None
    
    def get_user_attribute_by_alias(self, alias: str) -> UserAttribute | None:
        h = queries.ArgHelper()

        with queries.connected() as (conn, cursor):
            cursor.execute(f"""
                SELECT user_attribute_id
                FROM user_attribute_alias
                WHERE
                    list_id = {h|self.id}
                    AND alias = {h|alias}
            """, h.steal())

            result: UserAttributeAliasResultT | None = cursor.fetchone()
        
        if result is None:
            return None
        
        return self.get_user_attribute_by_id(result['user_attribute_id'])

    def get_user_attribute_by_syn(self, syn: str) -> UserAttribute | None:
        return (
            self.get_user_attribute_by_name(syn)
            or self.get_user_attribute_by_alias(syn)
        )


    # --- Tasks ---

    def _fetch_tasks_from_table(self, where: Callable[[queries.ArgHelper], str] | None) -> list[TaskResultT]:
        h = queries.ArgHelper()
        
        with queries.connected() as (conn, cursor):
            cursor.execute(f"""
                SELECT *
                FROM task
                WHERE 
                    list_id = {h|self.id}
                    {f"AND {where(h)}" if where is not None else ""}
            """, h.steal())

            result: list[TaskResultT] = cursor.fetchall()

        return result
    
    def _task_data_to_obj(self, data: TaskResultT) -> Task:
        return Task(
            list=self,
            id=data['id'],
            name=data['name']
        )
    
    def get_tasks(self, where: Callable[[queries.ArgHelper], str] | None = None) -> list[Task]:
        return [
            self._task_data_to_obj(data) 
            for data in self._fetch_tasks_from_table(where)
        ]

    def get_task_by_id(self, id: int) -> Task | None:
        data = self._fetch_tasks_from_table(lambda h: f"id = {h|id}")
        return self._task_data_to_obj(data[0]) if data else None
    
    def get_task_by_name(self, name: str) -> Task | None:
        data = self._fetch_tasks_from_table(lambda h: f"name = {h|name}")
        return self._task_data_to_obj(data[0]) if data else None

    def get_task_by_alias(self, alias: str) -> Task | None:
        alias = text.sanitize(alias)
        h = queries.ArgHelper()

        with queries.connected() as (conn, cursor):
            cursor.execute(f"""
                SELECT task_id
                FROM task_alias
                WHERE 
                    list_id = {h|self.id}
                    AND alias = {h|alias}
            """, h.steal())

            result: TaskAliasResultT | None = cursor.fetchone()

        if result is None:
            return None
        
        return self.get_task_by_id(result['task_id'])