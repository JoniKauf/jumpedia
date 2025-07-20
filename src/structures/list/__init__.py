from collections import defaultdict
from contextlib import nullcontext
from dataclasses import dataclass, field
from enum import Enum, auto
from functools import cached_property
import itertools
import json
from multiprocessing.util import Finalize
from typing import TYPE_CHECKING, AbstractSet, Any, Callable, ClassVar, Final, Iterable, Literal, Mapping, Never, NotRequired, Self, TypedDict

from database import queries 
from database.simple_orm import Arg, Rows
from errors.feedback import feedbacks
from structures.attributes.slot_type import SlotType, SlotTypeT
from structures.base_structure import BaseStructure
from structures.attributes import ANY_ATTRIBUTE, AnyAttributeT, BaseAttribute, RawCollectionNodesT, Uniqueness, Uniqueness
from structures.attributes import collection
from structures.attributes.collection import Collection, CollectionNode, CollectionNodesT
from structures.attributes.static_attribute import StaticAttribute
from structures.attributes.task_attribute import TaskAttribute
from structures.attributes.user_attribute import UserAttribute
from structures.list import UserCollectionNodeT, UserCollectionNodesT
from structures.task import Task
from utils import metautils, parsetools, text
from structures import attributes, task
from database import typed
import structures.list as list_package


import pickle

if TYPE_CHECKING:
    from structures.community import Community


MIN_NAME_LENGTH: Final[int] = 2
MAX_NAME_LENGTH: Final[int] = 64
MAX_ATTRIBUTES: Final[int] = 3
MAX_TASKS: Final[int] = 1


# --- Collection Types --- #


@dataclass(frozen=True, kw_only=True)
class List(BaseStructure):
    __structure_name__: ClassVar[str] = "list"

    community: 'Community'
    id: int
    name: str
    
    @property
    def identity(self) -> tuple[int, ...]:
        return (self.id, *self.community.identity)


    # --- All Attributes ---

    def _fetch_from_attribute_table[T: typed.BaseAttribute](
        self, 
        table_type: type[T], 
        where: Callable[[Arg], str] | None
    ) -> Rows[T]:
        with queries.connected() as c:
            c.execute(lambda arg: f"""
                SELECT *
                FROM {table_type}
                WHERE 
                    {table_type.list_id} = {arg(self.id)}
                    {f"AND {where(arg)}" if where is not None else ""}
            """)

            return c.fetchall(table_type)
        
    def _attribute_row_to_obj[T: BaseAttribute](
        self, 
        type: type[T], 
        row: typed.BaseAttribute
    ) -> T:
        return type(
            list=self,
            id=row.id,
            name=row.name,
            slot_type=SlotType.get_by_id(row.slot_type),
            position=row.position,
            min_slots=row.min_slots,
            max_slots=row.max_slots,
            uniqueness=Uniqueness.get_by_value(row.uniqueness)
        )
    
    def get_attributes[T: BaseAttribute](self, type: type[T]) -> tuple[T, ...]:
        return tuple(
            self._attribute_row_to_obj(type, row)
            for row in self._fetch_from_attribute_table(type.tables.attribute, None)
        )

    def get_attribute_by_id[T: BaseAttribute](self, type: type[T], id: int) -> T | None:
        table_type = type.tables.attribute
        rows = self._fetch_from_attribute_table(table_type, lambda arg: f"{table_type.id} = {arg(id)}")
        return self._attribute_row_to_obj(type, rows[0]) if rows else None

    def get_attribute_by_name[T: BaseAttribute](self, type: type[T], name: str) -> T | None:
        table_type = type.tables.attribute
        rows = self._fetch_from_attribute_table(table_type, lambda arg: f"{table_type.name} = {arg(name)}")
        return self._attribute_row_to_obj(type, rows[0]) if rows else None
    
    def get_attribute_by_alias[T: BaseAttribute](self, type: type[T], alias: str) -> T | None:
        alias_table_type = type.tables.attribute_alias

        with queries.connected() as c:
            c.execute(lambda arg: f"""
                SELECT {alias_table_type.attribute_id}
                FROM {alias_table_type}
                WHERE 
                    {alias_table_type.list_id} = {arg(self.id)}
                    AND {alias_table_type.alias} = {arg(alias)}
            """)

            row = c.fetchone(alias_table_type)

        if row is None:
            return None
        
        return self.get_attribute_by_id(type, row.attribute_id)
    
    def get_attribute_by_syn[T: BaseAttribute](self, type: type[T], syn: str) -> T | None:
        return (
            self.get_attribute_by_name(type, syn)
            or self.get_attribute_by_alias(type, syn)
        )

    @overload
    def get_all_attributes(self) -> list[AnyAttributeT]:
        return itertools.chain.from_iterable(
            self.get_attributes(type)
            for type in ANY_ATTRIBUTE
        )

    def get_attributes_categorized(
        self, 
        where: Callable[[Arg], str] | None = None
    ) -> tuple[
        tuple[type[StaticAttribute], list[StaticAttribute]], 
        tuple[type[TaskAttribute], list[TaskAttribute]], 
        tuple[type[UserAttribute], list[UserAttribute]]
    ]:
        return (
            (StaticAttribute, self.get_static_attributes(where)),
            (TaskAttribute, self.get_task_attributes(where)),
            (UserAttribute, self.get_user_attributes(where))
        )

    def get_any_attribute_by_name(self, name: str) -> AnyAttributeT | None:
        return 
        
    def get_any_attribute_by_alias(self, alias: str) -> AnyAttributeT | None:
        return (
            self.get_static_attribute_by_alias(alias)
            or self.get_task_attribute_by_alias(alias)
            or self.get_user_attribute_by_alias(alias)
        )

    def get_any_attribute_by_syn(self, syn: str) -> AnyAttributeT | None:
        return (
            self.get_static_attribute_by_syn(syn)
            or self.get_task_attribute_by_syn(syn)
            or self.get_user_attribute_by_syn(syn)
        )

    def _validate_attribute_attributes(
        self,
        name: str,
        aliases: frozenset[str],
        max_slots: int,
        min_slots: int = 0
    ) -> int:
        with self.locked:
            attrs = self.get_all_attributes()

            if len(attrs) >= list_package.MAX_ATTRIBUTES:
                raise feedbacks.temp("Max attributes reached")
            
            for syn in (name, *aliases):
                if len(syn) > attributes.MAX_SYN_LEN:
                    raise feedbacks.temp("Max syn length exceeded")
                
                if self.get_any_attribute_by_syn(syn) is not None:
                    raise feedbacks.temp(f"Attribute name or alias `{syn}` already used as name or alias of different attribute")

            if not (1 <= max_slots <= attributes.MAX_SLOTS):
                raise feedbacks.temp("Max slots must be between 1 and 32 inclusive")

            if not (0 <= min_slots <= max_slots):
                raise feedbacks.temp("Min slots must be between 0 and max slots inclusive")
            
            return max(attr.position for attr in attrs) + 1 if attrs else 1
        
        
    def _generic_delete_attribute(self, name: str, table: type[typed.BaseAttribute]) -> None:
        with self.locked, queries.connected() as c:
            if issubclass(table, TaskAttribute):
                attr = self.get_task_attribute_by_name(name)
            else:
                attr = self.get_user_attribute_by_name(name)

            if attr is None:
                raise feedbacks.temp("Attribute not found!")
            
            with attr.locked:  # type: ignore
                c.execute(lambda arg: f"""
                    DELETE FROM {table}
                    WHERE 
                        {table.list_id} = {arg(self.id)}
                        AND {table.id} = {arg(attr.id)}
                """)


    # --- Static Attribute ---

    def create_static_attribute[T: SlotTypeT](
        self,
        name: str,
        aliases: frozenset[str],
        value_type: SlotType[T],
        min_slots: int,
        max_slots: int,
        uniqueness: Uniqueness
    ) -> StaticAttribute[T]:
        """This method should not be public to the user!"""
        with self.locked:
            assert self.get_tasks() == []
            
            position = self._validate_attribute_attributes(name, aliases, max_slots, min_slots)

            Tbl = typed.StaticAttribute

            with queries.connected() as c:
                c.execute(lambda arg: f"""
                    INSERT INTO {Tbl} (
                        {Tbl.list_id},
                        {Tbl.name},
                        {Tbl.slot_type},
                        {Tbl.position},
                        {Tbl.min_slots},
                        {Tbl.max_slots},
                        {Tbl.uniqueness},
                    )
                    VALUES (
                        {arg(self.id)},
                        {arg(name)},
                        {arg(value_type.id)},
                        {arg(position)},
                        {arg(min_slots)},
                        {arg(max_slots)},
                        {arg(uniqueness.value)}
                    )
                """)

                attribute_id: int = c.last_generated_id

                SAAT = typed.StaticAttributeAlias

                if aliases:
                    c.execute(lambda arg: f"""
                        INSERT INTO {SAAT} (
                            {SAAT.attribute_id},
                            {SAAT.list_id},
                            {SAAT.alias}
                        ) 
                        VALUES 
                            {','.join(f"({arg(attribute_id)}, {arg(self.id)}, {arg(alias)})" for alias in aliases)}
                    """)

                obj = StaticAttribute(
                    list=self,
                    id=attribute_id,
                    name=name,
                    slot_type=value_type,
                    position=position,
                    min_slots=0,
                    max_slots=max_slots,
                    uniqueness=uniqueness,
                )

                return obj
            
    def delete_static_attribute(self) -> Never:
        raise feedbacks.temp("Static attribute cannot be deleted!")

    def _fetch_static_attribute_rows_from_table(self, where: Callable[[Arg], str] | None) -> Rows[typed.StaticAttribute]:
        with queries.connected() as c:
            c.execute(lambda arg: f"""
                SELECT *
                FROM {typed.StaticAttribute}
                WHERE 
                    {typed.StaticAttribute.list_id} = {arg(self.id)}
                    {f"AND {where(arg)}" if where is not None else ""}
            """)

            result = c.fetchall(typed.StaticAttribute)

        return result
    
    def _static_attribute_row_to_obj(self, row: typed.StaticAttribute) -> StaticAttribute:
        return StaticAttribute(
            list=self,
            id=row.id,
            name=row.name,
            slot_type=SlotType.get_by_id(row.slot_type),
            position=row.position,
            min_slots=row.min_slots,
            max_slots=row.max_slots,
            uniqueness=Uniqueness.get_by_value(row.uniqueness),
        )
    
    def get_static_attributes(self, where: Callable[[Arg], str] | None = None) -> list[StaticAttribute]:
        return [
            self._static_attribute_row_to_obj(data) 
            for data in self._fetch_static_attribute_rows_from_table(where)
        ]

    def get_static_attribute_by_id(self, id: int) -> StaticAttribute | None:
        rows = self._fetch_static_attribute_rows_from_table(lambda arg: f"{typed.StaticAttribute.id} = {arg(id)}")
        return self._static_attribute_row_to_obj(rows[0]) if rows else None
    
    def get_static_attribute_by_name(self, name: str) -> StaticAttribute | None:
        data = self._fetch_static_attribute_rows_from_table(lambda arg: f"{typed.StaticAttribute.name} = {arg(name)}")
        return self._static_attribute_row_to_obj(data[0]) if data else None

    def get_static_attribute_by_alias(self, alias: str) -> StaticAttribute | None:
        AttrAliasTable = typed.StaticAttributeAlias

        with queries.connected() as c:
            c.execute(lambda arg: f"""
                SELECT {AttrAliasTable.attribute_id}
                FROM {AttrAliasTable}
                WHERE
                    {AttrAliasTable.list_id} = {arg(self.id)}
                    AND {AttrAliasTable.alias} = {arg(alias)}
            """)

            result = c.fetchone(typed.StaticAttributeAlias)

        if result is None:
            return None
        
        return self.get_static_attribute_by_id(result.id)
    
    def get_static_attribute_by_syn(self, syn: str) -> StaticAttribute | None:
        return (
            self.get_static_attribute_by_name(syn)
            or self.get_static_attribute_by_alias(syn)
        )
    
    def get_static_name_attribute(self) -> StaticAttribute[str]:
        name_attribute = self.get_static_attribute_by_name(task.STATIC_NAME_ATTRIBUTE_NAME)
        assert name_attribute is not None
        return name_attribute
    
    def get_static_alias_attribute(self) -> StaticAttribute[str]:
        alias_attribute = self.get_static_attribute_by_name(task.STATIC_ALIASES_ATTRIBUTE_NAME)
        assert alias_attribute is not None
        return alias_attribute
    

    # --- Task Attributes ---
    
    def create_task_attribute[T: SlotTypeT](
        self,
        name: str,
        aliases: frozenset[str],
        value_type: SlotType[T],
        top_raw_nodes: RawCollectionNodesT[T],
        max_slots: int,
        uniqueness: Uniqueness
    ) -> TaskAttribute[T]:
        with self.locked:
            MIN_SLOTS = 0

            index = self._validate_attribute_attributes(name, aliases, max_slots, MIN_SLOTS)
 
            SAT = typed.TaskAttribute

            with queries.connected() as c:
                c.execute(lambda arg: f"""
                    INSERT INTO {SAT} (
                        {SAT.list_id},
                        {SAT.name},
                        {SAT.slot_type},
                        {SAT.position},
                        {SAT.min_slots},
                        {SAT.max_slots},
                        {SAT.uniqueness},
                    )
                    VALUES (
                        {arg(self.id)},
                        {arg(name)},
                        {arg(value_type.id)},
                        {arg(index)},
                        {arg(MIN_SLOTS)},
                        {arg(max_slots)},
                        {arg(uniqueness.value)},
                    )
                """)

                attribute_id: int = c.last_generated_id

                if aliases:
                    c.execute(lambda arg: f"""
                        INSERT INTO {TAAT} (
                            {TAAT.task_attribute_id},
                            {TAAT.list_id},
                            {TAAT.alias}
                        ) 
                        VALUES 
                            {','.join(f"""(
                                {arg(attribute_id)}, 
                                {arg(self.id)}, 
                                {arg(alias)})""" 
                            for alias in aliases)}
                    """)

                attribute = TaskAttribute(
                    list=self,
                    id=attribute_id,
                    name=name,
                    slot_type=value_type,
                    position=index,
                    min_slots=MIN_SLOTS,
                    max_slots=max_slots,
                    uniqueness=uniqueness
                )

                attribute.set_collection(top_raw_nodes)

                return attribute
    
    def delete_task_attribute(self, bad_name: str) -> None:
        self._generic_delete_attribute(typed.TaskAttribute, bad_name)
            
    def _fetch_task_attributes_from_table(self, where: Callable[[Arg], str] | None) -> queries.ManyRowsT:
        with queries.connected() as c:
            c.execute(lambda arg: f"""
                SELECT *
                FROM {typed.TaskAttribute}
                WHERE 
                    {typed.TaskAttribute.list_id} = {arg(self.id)}
                    {f"AND {where(arg)}" if where is not None else ""}
            """)

            return c.fetchall(typed.TaskAttribute)

    
    def _task_attribute_row_to_obj(self, data: queries.OneRowT) -> TaskAttribute:
        Tbl = typed.TaskAttribute

        return TaskAttribute(
            list=self,
            id=data[Tbl.id],
            name=data[Tbl.name],
            position=data[Tbl.position],
            slot_type=SlotType.get_by_id(data[Tbl.slot_type]),
            min_slots=data[Tbl.min_slots],
            max_slots=data[Tbl.max_slots],
            uniqueness=data[Tbl.uniqueness],
        )
    
    def get_task_attributes(self, where: Callable[[Arg], str] | None = None) -> list[TaskAttribute]:
        return [
            self._task_attribute_row_to_obj(data) 
            for data in self._fetch_task_attributes_from_table(where)
        ]

    def get_task_attribute_by_id(self, id: int) -> TaskAttribute | None:
        data = self._fetch_task_attributes_from_table(lambda arg: f"{typed.TaskAttribute.id} = {arg(id)}")
        return self._task_attribute_row_to_obj(data[0]) if data else None
    
    def get_task_attribute_by_name(self, name: str) -> TaskAttribute | None:
        data = self._fetch_task_attributes_from_table(lambda arg: f"{typed.TaskAttribute.name} = {arg(name)}")
        return self._task_attribute_row_to_obj(data[0]) if data else None

    def get_task_attribute_by_alias(self, alias: str) -> TaskAttribute | None:
        with queries.connected() as c:
            c.execute(lambda arg: f"""
                SELECT {typed.TaskAttributeAlias.task_attribute_id}
                FROM {typed.TaskAttributeAlias}
                WHERE
                    {typed.TaskAttributeAlias.list_id} = {arg(self.id)}
                    AND {typed.TaskAttributeAlias.alias} = {arg(alias)}
            """)

            result: queries.OneRowT | None = c.fetchone()

        if result is None:
            return None
        
        return self.get_task_attribute_by_id(result[typed.TaskAttributeAlias.task_attribute_id])

    def get_task_attribute_by_syn(self, syn: str) -> TaskAttribute | None:
        return (
            self.get_task_attribute_by_name(syn)
            or self.get_task_attribute_by_alias(syn)
        )
    

    # --- User Attributes ---

    def create_user_attribute[T: SlotTypeT](
        self,
        name: str,
        aliases: frozenset[str],
        value_type: SlotType[T],
        top_raw_nodes: RawCollectionNodesT[T],
        max_slots: int,
        uniqueness: Uniqueness
    ) -> UserAttribute[T]:
        with self.locked:
            MIN_SLOTS = 0
            position = self._validate_attribute_attributes(name, aliases, max_slots, MIN_SLOTS)

            with queries.connected() as c:
                Tbl = typed.UserAttribute

                c.execute(lambda arg: f"""
                    INSERT INTO {Tbl} (
                        {Tbl.list_id},
                        {Tbl.name},
                        {Tbl.slot_type},
                        {Tbl.position},
                        {Tbl.min_slots},
                        {Tbl.max_slots},
                        {Tbl.uniqueness}
                    )
                    VALUES (
                        {arg(self.id)},
                        {arg(name)},
                        {arg(value_type.id)},
                        {arg(position)},
                        {arg(MIN_SLOTS)},
                        {arg(max_slots)},
                        {arg(uniqueness.value)}
                    )
                """)

                attribute_id: int = c.lastrowid  # type: ignore

                if aliases:
                    Tbl = typed.UserAttributeAlias

                    c.execute(lambda arg: f"""
                        INSERT INTO {Tbl} (
                            {Tbl.user_attribute_id},
                            {Tbl.list_id},
                            {Tbl.alias}
                        ) 
                        VALUES 
                            {','.join(f"({arg(attribute_id)}, {arg(self.id)}, {arg(alias)})" for alias in aliases)}
                        )
                    """)

                user_attribute = UserAttribute(
                    list=self,
                    id=attribute_id,
                    name=name,
                    slot_type=value_type,
                    position=position,
                    min_slots=MIN_SLOTS,
                    max_slots=max_slots,
                    uniqueness=uniqueness
                )

                user_attribute.set_collection(top_raw_nodes)
                
                return user_attribute
    
    def delete_user_attribute(self, bad_name: str) -> None:
        self._generic_delete_attribute(UserAttribute, bad_name)

    def _fetch_user_attributes_from_table(self, where: Callable[[Arg], str] | None) -> queries.ManyRowsT: 
        with queries.connected() as c:
            c.execute(lambda arg: f"""
                SELECT *
                FROM {typed.UserAttribute}
                WHERE 
                    {typed.UserAttribute.list_id} = {arg(self.id)}
                    {f"AND {where(arg)}" if where is not None else ""}
            """)

            result: queries.ManyRowsT = c.fetchall()

        return result
    
    def _user_attribute_data_to_obj(self, data: queries.OneRowT) -> UserAttribute:
        UAT = typed.UserAttribute

        return UserAttribute(
            list=self,
            id=data[UAT.id],
            name=data[UAT.name],
            position=data[UAT.position],
            slot_type=SlotType.get_by_id(data[UAT.slot_type]),
            min_slots=data[UAT.min_slots],
            max_slots=data[UAT.max_slots],
            uniqueness=data[UAT.uniqueness]
        )
    
    def get_user_attributes(self, where: Callable[[Arg], str] | None = None) -> list[UserAttribute]:
        return [
            self._user_attribute_data_to_obj(data) 
            for data in self._fetch_user_attributes_from_table(where)
        ]

    def get_user_attribute_by_id(self, id: int) -> UserAttribute | None:
        data = self._fetch_user_attributes_from_table(lambda arg: f"{typed.UserAttribute.id} = {arg(id)}")
        return self._user_attribute_data_to_obj(data[0]) if data else None
    
    def get_user_attribute_by_name(self, name: str) -> UserAttribute | None:
        data = self._fetch_user_attributes_from_table(lambda arg: f"{typed.UserAttribute.name} = {arg(name)}")
        return self._user_attribute_data_to_obj(data[0]) if data else None
    
    def get_user_attribute_by_alias(self, alias: str) -> UserAttribute | None:
        with queries.connected() as c:
            c.execute(lambda arg: f"""
                SELECT {typed.UserAttributeAlias.user_attribute_id}
                FROM {typed.UserAttributeAlias}
                WHERE
                    {typed.UserAttributeAlias.list_id} = {arg(self.id)}
                    AND {typed.UserAttributeAlias.alias} = {arg(alias)}
            """)

            result: queries.OneRowT | None = c.fetchone()
        
        if result is None:
            return None
        
        return self.get_user_attribute_by_id(result[typed.UserAttributeAlias.user_attribute_id])

    def get_user_attribute_by_syn(self, syn: str) -> UserAttribute | None:
        return (
            self.get_user_attribute_by_name(syn)
            or self.get_user_attribute_by_alias(syn)
        )


    # --- Tasks ---

    def create_task(
        self, 
        name: str, 
        aliases: frozenset[str], 
        attribute_value_mapping: Mapping[TaskAttribute, list[SlotTypeT]]
    ) -> Task:
        with self.locked:
            if len(self.get_tasks()) >= list_package.MAX_TASKS:
                raise feedbacks.temp("Task limit reached")
            
            for syn in (name, *aliases):
                if self.get_task_by_syn(syn) is not None:
                    raise feedbacks.temp(f"Task with name or alias {syn} already exists")
                
            for attr in self.get_task_attributes():
                if attr.required and attr not in attribute_value_mapping:
                    raise feedbacks.temp(f"Attribute {attr} is required (min >= 1 slots) but it received no values")
                
            with queries.connected() as c:
                c.execute(lambda arg: f"""
                    INSERT INTO {typed.Task} (
                        {typed.Task.list_id},
                        {typed.Task.name}
                    )
                    VALUES (
                        {arg(self.id)},
                        {arg(name)}
                    )
                """)

                task_id: int = c.lastrowid  # type: ignore
                
                if aliases:
                    c.execute(lambda arg: f"""
                        INSERT INTO {typed.TaskAlias} (
                            {typed.TaskAlias.task_id},
                            {typed.TaskAlias.list_id},
                            {typed.TaskAlias.alias}
                        ) 
                        VALUES 
                            {','.join(f"({arg(task_id)}, {arg(self.id)}, {arg(alias)})" for alias in aliases)}        
                    """)

                if attribute_value_mapping:
                    Tbl = typed.TaskAttributeTaskValue
                    
                    c.execute(lambda arg: f"""
                        INSERT INTO {Tbl} (
                            {Tbl.task_id},
                            {Tbl.task_attribute_id},
                            {Tbl.value}
                        )
                        VALUES 
                            {','.join(f"({arg(task_id)}, {arg(attr.id)}, {arg(pickle.dumps(v))})" for attr, v in attribute_value_mapping.items())}
                    """)

            return Task(
                list=self,
                id=task_id,
                name=name
            )
        
    def delete_task(self, id: int) -> bool:
        with self.locked, queries.connected() as c:
            c.execute(lambda arg: f"""
                DELETE FROM {typed.Task}
                WHERE 
                    {typed.Task.list_id} = {arg(self.id)}
                    AND {typed.Task.id} = {arg(id)}
            """)

            return c.affected_row_count > 0
        
    def _fetch_tasks_from_table(self, where: Callable[[Arg], str] | None) -> queries.ManyRowsT:
        with queries.connected() as c:
            c.execute(lambda arg: f"""
                SELECT *
                FROM {typed.Task}
                WHERE 
                    {typed.Task.list_id} = {arg(self.id)}
                    {f"AND {where(arg)}" if where is not None else ""}
            """)

            result = c.fetchall(typed.Task)

        return result
    
    def _task_row_to_obj(self, row: typed.Task) -> Task:
        return Task(
            list=self,
            id=row[typed.Task.id],
            name=row[typed.Task.name]
        )
    
    def get_tasks(self, where: Callable[[Arg], str] | None = None) -> list[Task]:
        return [
            self._task_row_to_obj(data) 
            for data in self._fetch_tasks_from_table(where)
        ]

    def get_task_by_id(self, id: int) -> Task | None:
        data = self._fetch_tasks_from_table(lambda arg: f"{typed.Task.id} = {arg(id)}")
        return self._task_row_to_obj(data[0]) if data else None
    
    def get_task_by_name(self, name: str) -> Task | None:
        data = self._fetch_tasks_from_table(lambda arg: f"{typed.Task.name} = {arg(name)}")
        return self._task_row_to_obj(data[0]) if data else None

    def get_task_by_alias(self, alias: str) -> Task | None:
        with queries.connected() as c:
            c.execute(lambda arg: f"""
                SELECT {typed.TaskAlias.task_id}
                FROM {typed.TaskAlias}
                WHERE 
                    {typed.TaskAlias.list_id} = {arg(self.id)}
                    AND {typed.TaskAlias.alias} = {arg(alias)}
            """)

            result = c.fetchone(typed.TaskAlias)

        if result is None:
            return None
        
        return self.get_task_by_id(result.task_id)
    
    def get_task_by_syn(self, syn: str) -> Task | None:
        return (
            self.get_task_by_name(syn) or
            self.get_task_by_alias(syn)
        )