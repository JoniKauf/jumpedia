from collections import defaultdict
from contextlib import nullcontext
from dataclasses import dataclass, field
from enum import Enum, auto
from functools import cached_property
import itertools
import json
from multiprocessing.util import Finalize
from typing import TYPE_CHECKING, AbstractSet, Any, Callable, ClassVar, Final, Iterable, Literal, Mapping, Never, NotRequired, Self, TypedDict, overload

from database import queries 
from database.simple_orm import Arg, Rows
from errors.feedback import feedbacks
from structures.attributes.slot_type import SlotType, SlotTypeT
from structures.base_structure import BaseStructure
from structures.attributes import ANY_ATTRIBUTE, AnyAttributeT, AttributeValueParseTypesT, BaseAttribute, BaseNonStaticAttribute, RawCollectionNodesT
from structures.attributes.collection import Collection, CollectionNode, CollectionNodesT
from structures.attributes.static_attribute import StaticAttribute
from structures.attributes.task_attribute import TaskAttribute
from structures.attributes.user_attribute import UserAttribute
from structures.errors import StructureNotFoundError
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
            c.execute(lambda arg: t"""
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
            name=row.real_name,
            slot_type=SlotType.get_by_id(row.slot_type),
            position=row.position,
            min_slots=row.min_slots,
            max_slots=row.max_slots
        )
    
    def get_attributes[T: BaseAttribute](self, type: type[T]) -> set[T]:
        return {
            self._attribute_row_to_obj(type, row)
            for row in self._fetch_from_attribute_table(type.tables.attribute, None)
        }

    def get_attribute_by_id[T: BaseAttribute](self, type: type[T], id: int) -> T | None:
        table_type = type.tables.attribute
        rows = self._fetch_from_attribute_table(table_type, lambda arg: f"{table_type.id} = {arg(id)}")
        return self._attribute_row_to_obj(type, rows[0]) if rows else None

    def get_attribute_by_norm_name[T: BaseAttribute](self, type: type[T], norm_name: str) -> T | None:
        table_type = type.tables.attribute
        rows = self._fetch_from_attribute_table(table_type, lambda arg: f"{table_type.norm_name} = {arg(norm_name)}")
        return self._attribute_row_to_obj(type, rows[0]) if rows else None
    
    def get_attribute_by_norm_alias[T: BaseAttribute](self, type: type[T], norm_alias: str) -> T | None:
        alias_table_type = type.tables.attribute_alias

        with queries.connected() as c:
            c.execute(lambda arg: t"""
                SELECT {alias_table_type.attribute_id}
                FROM {alias_table_type}
                WHERE 
                    {alias_table_type.list_id} = {arg(self.id)}
                    AND {alias_table_type.norm_alias} = {arg(norm_alias)}
            """)

            row = c.fetchone(alias_table_type)

        if row is None:
            return None
        
        return self.get_attribute_by_id(type, row.attribute_id)
    
    def get_attribute_by_norm_syn[T: BaseAttribute](self, type: type[T], norm_syn: str) -> T | None:
        return (
            self.get_attribute_by_norm_name(type, norm_syn)
            or self.get_attribute_by_norm_alias(type, norm_syn)
        )

    def get_all_attributes_flat(self) -> tuple[AnyAttributeT, ...]:
        return tuple(
            attr
            for type in ANY_ATTRIBUTE
                for attr in self.get_attributes(type)
        )
        
    
    def get_all_attributes(self) -> tuple[set[StaticAttribute], set[TaskAttribute], set[UserAttribute]]:
        return tuple(
            self.get_attributes(type)
            for type in ANY_ATTRIBUTE
        )  # type: ignore

    def get_any_attribute_by_id(self, id: int) -> AnyAttributeT | None:
        for type in ANY_ATTRIBUTE:
            attr = self.get_attribute_by_id(type, id)

            if attr is not None:
                return attr
        
    def get_any_attribute_by_norm_name(self, norm_name: str) -> AnyAttributeT | None:
        for type in ANY_ATTRIBUTE:
            attr = self.get_attribute_by_norm_name(type, norm_name)
            
            if attr is not None:
                return attr
        
    def get_any_attribute_by_norm_alias(self, norm_alias: str) -> AnyAttributeT | None:
        for type in ANY_ATTRIBUTE:
            attr = self.get_attribute_by_norm_alias(type, norm_alias)
            
            if attr is not None:
                return attr

    def get_any_attribute_by_norm_syn(self, norm_syn: str) -> AnyAttributeT | None:
        for type in ANY_ATTRIBUTE:
            attr = self.get_attribute_by_norm_syn(type, norm_syn)
            
            if attr is not None:
                return attr

    @overload
    def create_attribute[T: StaticAttribute, TSlot: SlotTypeT](
        self, 
        type: type[T],
        raw_name: str,
        raw_aliases: frozenset[str],
        slot_type: SlotType[TSlot],
        max_slots: int,
        *,
        min_slots: int
    ) -> T:
        pass

    @overload
    def create_attribute[T: BaseNonStaticAttribute, TSlot: SlotTypeT](
        self, 
        type: type[T],
        raw_name: str,
        raw_aliases: frozenset[str],
        slot_type: SlotType[TSlot],
        max_slots: int,
        *,
        top_raw_nodes: RawCollectionNodesT
    ) -> T:
        pass

    def create_attribute[T: BaseAttribute, TSlot: SlotTypeT](
        self, 
        type: type[T],
        raw_name: str,
        raw_aliases: frozenset[str],
        slot_type: SlotType[TSlot],
        max_slots: int,
        *,
        min_slots: int = 0,
        top_raw_nodes: RawCollectionNodesT = frozenset()
    ) -> T:  # Higher kinded attributes not supported yet, otherwise T[TSlot]
        (real_name, *real_aliases), (norm_name, *norm_aliases) = text.raws_to_unique_reals_and_norms(*(raw_name, *raw_aliases))

        del raw_name
        del raw_aliases

        with self.locked:
            attrs = self.get_all_attributes_flat()

            if len(attrs) >= list_package.MAX_ATTRIBUTES:
                raise feedbacks.temp("Max attributes reached")
            
            for syn in (norm_name, *norm_aliases):
                if len(syn) > attributes.MAX_SYN_LEN:
                    raise feedbacks.temp("Max syn length exceeded")
                
                if self.get_any_attribute_by_norm_syn(syn) is not None:
                    raise feedbacks.temp(f"Attribute name or alias `{syn}` already used as name or alias of different attribute")

            if not (1 <= max_slots <= attributes.MAX_SLOTS):
                raise feedbacks.temp("Max slots must be between 1 and 32 inclusive")
            
            if min_slots != 0:
                if not type.allow_min_slots_on_creation:
                    raise feedbacks.temp("Not allowed to set min_slots")

                if not (0 <= min_slots <= attributes.MAX_SLOTS):
                    raise feedbacks.temp("Min slots wrong")

            index = max(attr.position for attr in attrs) + 1 if attrs else 1

            AttributeTbl = type.tables.attribute

            with queries.connected() as c:
                c.execute(lambda arg: t"""
                    INSERT INTO {AttributeTbl} (
                        {AttributeTbl.list_id},
                        {AttributeTbl.norm_name},
                        {AttributeTbl.real_name},
                        {AttributeTbl.slot_type},
                        {AttributeTbl.position},
                        {AttributeTbl.min_slots},
                        {AttributeTbl.max_slots},
                    )
                    VALUES (
                        {arg(self.id)},
                        {arg(norm_name)},
                        {arg(real_name)},
                        {arg(slot_type.id)},
                        {arg(index)},
                        {arg(min_slots)},
                        {arg(max_slots)}
                    )
                """)

                attribute_id = c.last_generated_id

                if norm_aliases:
                    AttributeAliasTbl = type.tables.attribute_alias
                    count = len(norm_aliases)

                    c.executemany(lambda args: t"""
                        INSERT INTO {AttributeAliasTbl} (
                            {AttributeAliasTbl.attribute_id},
                            {AttributeAliasTbl.list_id},
                            {AttributeAliasTbl.norm_alias},
                            {AttributeAliasTbl.real_alias}
                        ) 
                        VALUES (
                            {args(itertools.repeat(attribute_id, count))},
                            {args(itertools.repeat(self.id, count))},
                            {args(norm_aliases)},
                            {args(real_aliases)} 
                        )
                    """)

                attribute = type(
                    list=self,
                    id=attribute_id,
                    name=real_name,
                    slot_type=slot_type,
                    position=index,
                    min_slots=min_slots,
                    max_slots=max_slots
                )

                if top_raw_nodes:
                    if not isinstance(attribute, BaseNonStaticAttribute):
                        raise feedbacks.temp("Not CollectionAttribute")
                    
                    attribute.set_collection(top_raw_nodes)
                    
                return attribute

    def delete_attribute[T: BaseAttribute](self, type: type[T], attribute_id: int) -> bool:
        AttributeTbl = type.tables.attribute

        with self.locked, queries.connected() as c:
            c.execute(lambda arg: t"""
                DELETE FROM {AttributeTbl}
                WHERE {AttributeTbl.list_id} = {arg(self.id)}
                AND {AttributeTbl.id} = {arg(attribute_id)}
            """)

            return c.affected_row_count > 0

    def _cook_raw_attribute_value_mapping(
        self, 
        raw_attribute_value_mapping: dict[int, AttributeValueParseTypesT]
    ) -> dict[TaskAttribute, list[SlotTypeT]]:
        id_to_attr = {attr.id: attr for attr in self.get_attributes(TaskAttribute)}
            
        # Check if all required attributess are given
        for attr in id_to_attr.values():
            if attr.required and attr.id not in raw_attribute_value_mapping:
                raise feedbacks.temp(f"Attribute {attr} is required (min >= 1 slots) but it received no values")
        
        if not raw_attribute_value_mapping:
            return {}
        
        attribute_value_mapping: dict[TaskAttribute, list[SlotTypeT]] = {}
        
        # Convert ids to attributes and validate value
        for attr_id, v in raw_attribute_value_mapping.items():
            if attr_id not in id_to_attr:
                raise feedbacks.temp("Attribute id not found")
            
            attr = id_to_attr[attr_id]
            v = attr.value_from_loaded(v)

            attribute_value_mapping[attr] = v

        return attribute_value_mapping
    
    # --- Tasks ---

    def create_task(
        self, 
        raw_name: str, 
        raw_aliases: frozenset[str], 
        raw_attribute_value_mapping: dict[int, AttributeValueParseTypesT]
    ) -> Task:
        (real_name, *real_aliases), (norm_name, *norm_aliases) = text.raws_to_unique_reals_and_norms((raw_name, *raw_aliases))
        
        del raw_name
        del raw_aliases

        with self.locked:
            all_tasks = self.get_tasks()

            if len(all_tasks) >= list_package.MAX_TASKS:
                raise feedbacks.temp("Task limit reached")

            attribute_value_mapping = self._cook_raw_attribute_value_mapping(raw_attribute_value_mapping)
                
            with queries.connected() as c:
                c.execute(lambda arg: t"""
                    INSERT INTO {typed.Task} (
                        {typed.Task.list_id},
                        {typed.Task.norm_name},
                        {typed.Task.real_name}
                    )
                    VALUES (
                        {arg(self.id)},
                        {arg(norm_name)},
                        {arg(real_name)}
                    )
                """)

                task_id = c.last_generated_id 
                
                if norm_aliases:
                    count = len(norm_aliases)

                    c.executemany(lambda args: t"""
                        INSERT INTO {typed.TaskAlias} (
                            {typed.TaskAlias.task_id},
                            {typed.TaskAlias.list_id},
                            {typed.TaskAlias.norm_alias},
                            {typed.TaskAlias.real_alias},
                        ) 
                        VALUES (
                            {args(itertools.repeat(task_id, count))}, 
                            {args(itertools.repeat(self.id, count))}, 
                            {args(norm_aliases)},
                            {args(real_aliases)}
                        )
                    """)

                if attribute_value_mapping:
                    TaskValueTbl = TaskAttribute.tables.attribute_task_value

                    # This is so clean I'm UwU-ing
                    attribute_id_args: list[int] = []
                    index_args: list[int] = []
                    slot_args: list[SlotTypeT] = []

                    for attr, v in attribute_value_mapping.items():
                        for i, slot in enumerate(v):
                            attribute_id_args.append(attr.id)
                            index_args.append(i)
                            slot_args.append(slot)

                    c.executemany(lambda args: t"""
                        INSERT INTO {TaskValueTbl} (
                            {TaskValueTbl.task_id},
                            {TaskValueTbl.attribute_id},
                            {TaskValueTbl.index},
                            {TaskValueTbl.slot}
                        )
                        VALUES (
                            {args(itertools.repeat(task_id, len(attribute_id_args)))},
                            {args(attribute_id_args)},
                            {args(index_args)},
                            {args(slot_args)}
                        )
                    """)

            return Task(
                list=self,
                id=task_id,
                name=real_name
            )
        
    def delete_task(self, id: int) -> bool:
        with self.locked, queries.connected() as c:
            c.execute(lambda arg: t"""
                DELETE FROM {typed.Task}
                WHERE 
                    {typed.Task.list_id} = {arg(self.id)}
                    AND {typed.Task.id} = {arg(id)}
            """)

            return c.affected_row_count > 0
    
    def _validate_task_syn(self, id: int, syn: str) -> Task:
        task_ = self.get_task_by_id(id)

        if task_ is None:
            raise StructureNotFoundError(id)
        
        if self.get_task_by_syn(syn) != task_:
            return 
    def edit_task(
        self, 
        id: int, 
        raw_name: str | None = None, 
        raw_aliases: frozenset[str] | None = None, 
        raw_attribute_value_mapping: dict[int, str] | None = None
    ) -> None:
        with self.locked:
            

            
            
            if raw_name is None and raw_aliases is None and raw_attribute_value_mapping is None:
                return
            
            syns: list[str] = []

            if raw_name:
                syns.append(raw_name)

            if raw_aliases:
                syns.extend(raw_aliases)

            (real_name, *real_aliases), (norm_name, *norm_aliases) = text.raws_to_unique_reals_and_norms(syns)

            
            
            
            
        
    def _fetch_tasks_from_table(self, where: Callable[[Arg], str] | None) -> Rows[typed.Task]:
        with queries.connected() as c:
            c.execute(lambda arg: t"""
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
            id=row.id,
            name=row.real_name
        )
    
    def get_tasks(self, where: Callable[[Arg], str] | None = None) -> set[Task]:
        return {
            self._task_row_to_obj(data) 
            for data in self._fetch_tasks_from_table(where)
        }

    def get_task_by_id(self, id: int) -> Task | None:
        data = self._fetch_tasks_from_table(lambda arg: f"{typed.Task.id} = {arg(id)}")
        return self._task_row_to_obj(data[0]) if data else None
    
    def get_task_by_name(self, name: str) -> Task | None:
        data = self._fetch_tasks_from_table(lambda arg: f"{typed.Task.name} = {arg(name)}")
        return self._task_row_to_obj(data[0]) if data else None

    def get_task_by_alias(self, alias: str) -> Task | None:
        with queries.connected() as c:
            c.execute(lambda arg: t"""
                SELECT {typed.TaskAlias.task_id}
                FROM {typed.TaskAlias}
                WHERE 
                    {typed.TaskAlias.list_id} = {arg(self.id)}
                    AND {typed.TaskAlias.alias} = {arg(alias)}
            """)

            row = c.fetchone(typed.TaskAlias)

        if row is None:
            return None
        
        return self.get_task_by_id(row.task_id)
    
    def get_task_by_syn(self, syn: str) -> Task | None:
        return (
            self.get_task_by_name(syn) or
            self.get_task_by_alias(syn)
        )