from collections import defaultdict
from contextlib import nullcontext
from dataclasses import dataclass, field
from enum import Enum, auto
from functools import cached_property
import json
from multiprocessing.util import Finalize
from typing import TYPE_CHECKING, AbstractSet, Any, Callable, ClassVar, Final, Iterable, Literal, Never, NotRequired, Self, TypedDict

from database import queries 
from errors.feedback import feedbacks
from structures.attributes.slot_type import SlotType, SlotTypeT
from structures.base_structure import BaseStructure
from structures.attributes import AnyAttributeT, RawCollectionNodesT, Uniqueness, UniquenessExtended
from structures.attributes import collection
from structures.attributes.base_attribute import BaseAttribute
from structures.attributes.collection import Collection, CollectionNode, CollectionNodesT
from structures.attributes.static_attribute import StaticAttribute
from structures.attributes.task_attribute import TaskAttribute
from structures.attributes.user_attribute import UserAttribute
from structures.list import UserCollectionNodeT, UserCollectionNodesT
from structures.task import Task
from utils import metautils, parsetools, text
from structures import attributes, task
from database import typed as typed
from database.typed import Tables as Tables
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

    def get_attributes(self, where: Callable[[queries.ArgHelper], str] | None = None) -> list[AnyAttributeT]:
        return [attr for _, attr_coll in self.get_attributes_categorized(where) for attr in attr_coll]

    def get_attributes_categorized(
        self, 
        where: Callable[[queries.ArgHelper], str] | None = None
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

    def get_attribute_by_name(self, name: str) -> AnyAttributeT | None:
        return (
            self.get_static_attribute_by_name(name)
            or self.get_user_attribute_by_name(name)
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

    def _validate_attribute_attributes(
        self,
        name: str,
        aliases: frozenset[str],
        max_slots: int,
        min_slots: int = 0
    ) -> int:
        with self.locked:
            attrs = self.get_attributes()

            if len(attrs) >= list_package.MAX_ATTRIBUTES:
                raise feedbacks.temp("Max attributes reached")
            
            for syn in (name, *aliases):
                if len(syn) > attributes.MAX_SYN_LEN:
                    raise feedbacks.temp("Max syn length exceeded")
                
                if self.get_attribute_by_syn(syn) is not None:
                    raise feedbacks.temp(f"Attribute name or alias `{syn}` already used as name or alias of different attribute")

            if not (1 <= max_slots <= attributes.MAX_SLOTS):
                raise feedbacks.temp("Max slots must be between 1 and 32 inclusive")

            if not (0 <= min_slots <= max_slots):
                raise feedbacks.temp("Min slots must be between 0 and max slots inclusive")
            
            return max(attr.position for attr in attrs) + 1 if attrs else 1
        
        
    def _generic_delete_attribute(self, attribute_type: type[TaskAttribute | UserAttribute], bad_name: str) -> None:
        from database import dbutils

        name = text.sanitize(bad_name)

        h = queries.ArgHelper()
        Tbl = dbutils.get_attribute_table(attribute_type)

        with self.locked, queries.connected() as (conn, cursor):
            if issubclass(attribute_type, TaskAttribute):
                attr = self.get_task_attribute_by_name(name)
            else:
                attr = self.get_user_attribute_by_name(name)

            if attr is None:
                raise feedbacks.temp("Attribute not found!")
            
            with attr.locked:  # type: ignore
                cursor.execute(f"""
                    DELETE FROM {Tbl}
                    WHERE 
                        {Tbl.list_id} = {h|self.id}
                        AND {Tbl.id} = {h|attr.id}
                """, h.steal())


    # --- Static Attribute ---

    def create_static_attribute[T: SlotTypeT](
        self,
        name: str,
        aliases: frozenset[str],
        value_type: SlotType[T],
        min_slots: int,
        max_slots: int,
        uniqueness: UniquenessExtended
    ) -> StaticAttribute[T]:
        """This method should not public to the user!"""
        with self.locked:
            assert self.get_tasks() == []
            
            position = self._validate_attribute_attributes(name, aliases, max_slots, min_slots)

            h = queries.ArgHelper()
            Tbl = Tables.StaticAttribute

            with queries.connected() as (conn, cursor):
                cursor.execute(f"""
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
                        {h|self.id},
                        {h|name},
                        {h|value_type.id},
                        {h|position},
                        {h|min_slots},
                        {h|max_slots},
                        {h|uniqueness.value}
                    )
                """, h.steal())

                attribute_id: int = cursor.lastrowid  # type: ignore

                SAAT = Tables.StaticAttributeAlias

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
                    slot_type=value_type,
                    position=position,
                    min_slots=0,
                    max_slots=max_slots,
                    uniqueness=uniqueness,
                )

                return obj
            
    def delete_static_attribute(self) -> Never:
        raise feedbacks.temp("Static attribute cannot be deleted!")

    def _fetch_static_attributes_from_table(self, where: Callable[[queries.ArgHelper], str] | None) -> queries.ManyRowsT:
        h = queries.ArgHelper()
        
        with queries.connected() as (conn, cursor):
            cursor.execute(f"""
                SELECT *
                FROM {Tables.StaticAttribute}
                WHERE 
                    {Tables.StaticAttribute.list_id} = {h|self.id}
                    {f"AND {where(h)}" if where is not None else ""}
            """, h.steal())

            result: queries.ManyRowsT = cursor.fetchall()

        return result
    
    def _static_attribute_data_to_obj(self, data: queries.OneRowT) -> StaticAttribute:
        SAT = Tables.StaticAttribute

        return StaticAttribute(
            list=self,
            id=data[SAT.id],
            name=data[SAT.name],
            slot_type=SlotType.get_by_id(data[SAT.slot_type]),
            position=data[SAT.position],
            min_slots=data[SAT.min_slots],
            max_slots=data[SAT.max_slots],
            uniqueness=data[SAT.uniqueness],
        )
    
    def get_static_attributes(self, where: Callable[[queries.ArgHelper], str] | None = None) -> list[StaticAttribute]:
        return [
            self._static_attribute_data_to_obj(data) 
            for data in self._fetch_static_attributes_from_table(where)
        ]

    def get_static_attribute_by_id(self, id: int) -> StaticAttribute | None:
        data = self._fetch_static_attributes_from_table(lambda h: f"{Tables.StaticAttribute.id} = {h|id}")
        return self._static_attribute_data_to_obj(data[0]) if data else None
    
    def get_static_attribute_by_name(self, name: str) -> StaticAttribute | None:
        data = self._fetch_static_attributes_from_table(lambda h: f"{Tables.StaticAttribute.name} = {h|name}")
        return self._static_attribute_data_to_obj(data[0]) if data else None

    def get_static_attribute_by_alias(self, alias: str) -> StaticAttribute | None:
        h = queries.ArgHelper()
        SAAT = Tables.StaticAttributeAlias

        with queries.connected() as (conn, cursor):
            cursor.execute(f"""
                SELECT {SAAT.static_attribute_id}
                FROM {SAAT}
                WHERE
                    {SAAT.list_id} = {h|self.id}
                    AND {SAAT.alias} = {h|alias}
            """, h.steal())

            result: queries.OneRowT | None = cursor.fetchone()

        if result is None:
            return None
        
        return self.get_static_attribute_by_id(result[SAAT.static_attribute_id])
    
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
        uniqueness: UniquenessExtended
    ) -> TaskAttribute[T]:
        with self.locked:
            MIN_SLOTS = 0

            index = self._validate_attribute_attributes(name, aliases, max_slots, MIN_SLOTS)
            
            h = queries.ArgHelper()
            SAT = Tables.TaskAttribute

            with queries.connected() as (conn, cursor):
                cursor.execute(f"""
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
                        {h|self.id},
                        {h|name},
                        {h|value_type.id},
                        {h|index},
                        {h|MIN_SLOTS},
                        {h|max_slots},
                        {h|uniqueness.value},
                    )
                """, h.steal())

                attribute_id: int = cursor.lastrowid  # type: ignore

                TAAT = Tables.TaskAttributeAlias

                if aliases:
                    cursor.execute(f"""
                        INSERT INTO {TAAT} (
                            {TAAT.task_attribute_id},
                            {TAAT.list_id},
                            {TAAT.alias}
                        ) 
                        VALUES 
                            {','.join(f"({h|attribute_id}, {h|self.id}, {h|alias})" for alias in aliases)}
                    """, h.steal())

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
        self._generic_delete_attribute(TaskAttribute, bad_name)
            
    def _fetch_task_attributes_from_table(self, where: Callable[[queries.ArgHelper], str] | None) -> queries.ManyRowsT:
        h = queries.ArgHelper()
        
        with queries.connected() as (conn, cursor):
            cursor.execute(f"""
                SELECT *
                FROM {Tables.TaskAttribute}
                WHERE 
                    {Tables.TaskAttribute.list_id} = {h|self.id}
                    {f"AND {where(h)}" if where is not None else ""}
            """, h.steal())

            result: queries.ManyRowsT = cursor.fetchall()

        return result
    
    def _task_attribute_data_to_obj(self, data: queries.OneRowT) -> TaskAttribute:
        Tbl = Tables.TaskAttribute

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
    
    def get_task_attributes(self, where: Callable[[queries.ArgHelper], str] | None = None) -> list[TaskAttribute]:
        return [
            self._task_attribute_data_to_obj(data) 
            for data in self._fetch_task_attributes_from_table(where)
        ]

    def get_task_attribute_by_id(self, id: int) -> TaskAttribute | None:
        data = self._fetch_task_attributes_from_table(lambda h: f"{Tables.TaskAttribute.id} = {h|id}")
        return self._task_attribute_data_to_obj(data[0]) if data else None
    
    def get_task_attribute_by_name(self, name: str) -> TaskAttribute | None:
        data = self._fetch_task_attributes_from_table(lambda h: f"{Tables.TaskAttribute.name} = {h|name}")
        return self._task_attribute_data_to_obj(data[0]) if data else None
    
    def get_task_attribute_by_alias(self, alias: str) -> TaskAttribute | None:
        h = queries.ArgHelper()

        with queries.connected() as (conn, cursor):
            cursor.execute(f"""
                SELECT {Tables.TaskAttributeAlias.task_attribute_id}
                FROM {Tables.TaskAttributeAlias}
                WHERE
                    {Tables.TaskAttributeAlias.list_id} = {h|self.id}
                    AND {Tables.TaskAttributeAlias.alias} = {h|alias}
            """, h.steal())

            result: queries.OneRowT | None = cursor.fetchone()

        if result is None:
            return None
        
        return self.get_task_attribute_by_id(result[Tables.TaskAttributeAlias.task_attribute_id])

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

            h = queries.ArgHelper()

            with queries.connected() as (conn, cursor):
                Tbl = Tables.UserAttribute

                cursor.execute(f"""
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
                        {h|self.id},
                        {h|name},
                        {h|value_type.id},
                        {h|position},
                        {h|MIN_SLOTS},
                        {h|max_slots},
                        {h|uniqueness.value}
                    )
                """, h.steal())

                attribute_id: int = cursor.lastrowid  # type: ignore

                if aliases:
                    Tbl = Tables.UserAttributeAlias

                    cursor.execute(f"""
                        INSERT INTO {Tbl} (
                            {Tbl.user_attribute_id},
                            {Tbl.list_id},
                            {Tbl.alias}
                        ) 
                        VALUES 
                            {','.join(f"({h|attribute_id}, {h|self.id}, {h|alias})" for alias in aliases)}
                        )
                    """, h.steal())

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

    def _fetch_user_attributes_from_table(self, where: Callable[[queries.ArgHelper], str] | None) -> queries.ManyRowsT:
        h = queries.ArgHelper()
        
        with queries.connected() as (conn, cursor):
            cursor.execute(f"""
                SELECT *
                FROM {Tables.UserAttribute}
                WHERE 
                    {Tables.UserAttribute.list_id} = {h|self.id}
                    {f"AND {where(h)}" if where is not None else ""}
            """, h.steal())

            result: queries.ManyRowsT = cursor.fetchall()

        return result
    
    def _user_attribute_data_to_obj(self, data: queries.OneRowT) -> UserAttribute:
        UAT = Tables.UserAttribute

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
    
    def get_user_attributes(self, where: Callable[[queries.ArgHelper], str] | None = None) -> list[UserAttribute]:
        return [
            self._user_attribute_data_to_obj(data) 
            for data in self._fetch_user_attributes_from_table(where)
        ]

    def get_user_attribute_by_id(self, id: int) -> UserAttribute | None:
        data = self._fetch_user_attributes_from_table(lambda h: f"{Tables.UserAttribute.id} = {h|id}")
        return self._user_attribute_data_to_obj(data[0]) if data else None
    
    def get_user_attribute_by_name(self, name: str) -> UserAttribute | None:
        data = self._fetch_user_attributes_from_table(lambda h: f"{Tables.UserAttribute.name} = {h|name}")
        return self._user_attribute_data_to_obj(data[0]) if data else None
    
    def get_user_attribute_by_alias(self, alias: str) -> UserAttribute | None:
        h = queries.ArgHelper()

        with queries.connected() as (conn, cursor):
            cursor.execute(f"""
                SELECT {Tables.UserAttributeAlias.user_attribute_id}
                FROM {Tables.UserAttributeAlias}
                WHERE
                    {Tables.UserAttributeAlias.list_id} = {h|self.id}
                    AND {Tables.UserAttributeAlias.alias} = {h|alias}
            """, h.steal())

            result: queries.OneRowT | None = cursor.fetchone()
        
        if result is None:
            return None
        
        return self.get_user_attribute_by_id(result[Tables.UserAttributeAlias.user_attribute_id])

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
        attribute_value_mapping: dict[TaskAttribute, list[SlotTypeT]]
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

            h = queries.ArgHelper()

            with queries.connected() as (conn, cursor):
                cursor.execute(f"""
                    INSERT INTO {Tables.Task} (
                        {Tables.Task.list_id},
                        {Tables.Task.name}
                    )
                    VALUES (
                        {h|self.id},
                        {h|name}
                    )
                """, h.steal())

                task_id: int = cursor.lastrowid  # type: ignore
                
                if aliases:
                    cursor.execute(f"""
                        INSERT INTO {Tables.TaskAlias} (
                            {Tables.TaskAlias.task_id},
                            {Tables.TaskAlias.list_id},
                            {Tables.TaskAlias.alias}
                        ) 
                        VALUES 
                            {','.join(f"({h|task_id}, {h|self.id}, {h|alias})" for alias in aliases)}        
                    """, h.steal())

                if attribute_value_mapping:
                    Tbl = Tables.TaskAttributeTaskValue
                    
                    cursor.execute(f"""
                        INSERT INTO {Tbl} (
                            {Tbl.task_id},
                            {Tbl.task_attribute_id},
                            {Tbl.value}
                        )
                        VALUES 
                            {','.join(f"({h|task_id}, {h|attr.id}, {h|pickle.dumps(v)})" for attr, v in attribute_value_mapping.items())}
                    """, h.steal())

            return Task(
                list=self,
                id=task_id,
                name=name
            )
        
    def delete_task(self, id: int) -> bool:
        with self.locked, queries.connected() as (conn, cursor):
            h = queries.ArgHelper()

            cursor.execute(f"""
                DELETE FROM {Tables.Task}
                WHERE 
                    {Tables.Task.list_id} = {h|self.id}
                    AND {Tables.Task.id} = {h|id}
            """, h.steal())

            return cursor.rowcount > 0
        
    def _fetch_tasks_from_table(self, where: Callable[[queries.ArgHelper], str] | None) -> queries.ManyRowsT:
        h = queries.ArgHelper()
        
        with queries.connected() as (conn, cursor):
            cursor.execute(f"""
                SELECT *
                FROM {Tables.Task}
                WHERE 
                    {Tables.Task.list_id} = {h|self.id}
                    {f"AND {where(h)}" if where is not None else ""}
            """, h.steal())

            result: queries.ManyRowsT = cursor.fetchall()

        return result
    
    def _task_data_to_obj(self, data: queries.OneRowT) -> Task:
        return Task(
            list=self,
            id=data[Tables.Task.id],
            name=data[Tables.Task.name]
        )
    
    def get_tasks(self, where: Callable[[queries.ArgHelper], str] | None = None) -> list[Task]:
        return [
            self._task_data_to_obj(data) 
            for data in self._fetch_tasks_from_table(where)
        ]

    def get_task_by_id(self, id: int) -> Task | None:
        data = self._fetch_tasks_from_table(lambda h: f"{Tables.Task.id} = {h|id}")
        return self._task_data_to_obj(data[0]) if data else None
    
    def get_task_by_name(self, name: str) -> Task | None:
        data = self._fetch_tasks_from_table(lambda h: f"{Tables.Task.name} = {h|name}")
        return self._task_data_to_obj(data[0]) if data else None

    def get_task_by_alias(self, alias: str) -> Task | None:
        h = queries.ArgHelper()

        with queries.connected() as (conn, cursor):
            cursor.execute(f"""
                SELECT {Tables.TaskAlias.task_id}
                FROM {Tables.TaskAlias}
                WHERE 
                    {Tables.TaskAlias.list_id} = {h|self.id}
                    AND {Tables.TaskAlias.alias} = {h|alias}
            """, h.steal())

            result: queries.OneRowT | None = cursor.fetchone()

        if result is None:
            return None
        
        return self.get_task_by_id(result[Tables.TaskAlias.task_id])
    
    def get_task_by_syn(self, syn: str) -> Task | None:
        return (
            self.get_task_by_name(syn) or
            self.get_task_by_alias(syn)
        )