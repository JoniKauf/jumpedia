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
from structures.attributes import ANY_ATTRIBUTE, AnyAttributeT, AttributeValueParseTypesT, BaseAttribute, RawCollectionNodesT, Uniqueness, Uniqueness, BaseNonStaticAttribute
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
            uniqueness=Uniqueness.get(row.uniqueness)
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
        
    def get_any_attribute_by_name(self, name: str) -> AnyAttributeT | None:
        for type in ANY_ATTRIBUTE:
            attr = self.get_attribute_by_name(type, name)
            
            if attr is not None:
                return attr
        
    def get_any_attribute_by_alias(self, alias: str) -> AnyAttributeT | None:
        for type in ANY_ATTRIBUTE:
            attr = self.get_attribute_by_alias(type, alias)
            
            if attr is not None:
                return attr

    def get_any_attribute_by_syn(self, syn: str) -> AnyAttributeT | None:
        for type in ANY_ATTRIBUTE:
            attr = self.get_attribute_by_syn(type, syn)
            
            if attr is not None:
                return attr

    @overload
    def create_attribute[T: StaticAttribute, TSlot: SlotTypeT](
        self, 
        type: type[T],
        name: str,
        aliases: frozenset[str],
        value_type: SlotType[TSlot],
        max_slots: int,
        uniqueness: Uniqueness,
        *,
        min_slots: int
    ) -> T:
        pass

    @overload
    def create_attribute[T: TaskAttribute | UserAttribute, TSlot: SlotTypeT](
        self, 
        type: type[T],
        name: str,
        aliases: frozenset[str],
        value_type: SlotType[TSlot],
        max_slots: int,
        uniqueness: Uniqueness,
        *,
        top_raw_nodes: RawCollectionNodesT[TSlot]
    ) -> T:
        pass

    def create_attribute[T: BaseAttribute, TSlot: SlotTypeT](
        self, 
        type: type[T],
        name: str,
        aliases: frozenset[str],
        value_type: SlotType[TSlot],
        max_slots: int,
        uniqueness: Uniqueness,
        *,
        min_slots: int = 0,
        top_raw_nodes: RawCollectionNodesT[TSlot] = frozenset()
    ) -> T:  # Higher kinded attributes not supported yet, otherwise T[TSlot]
        with self.locked:
            attrs = self.get_all_attributes_flat()

            if len(attrs) >= list_package.MAX_ATTRIBUTES:
                raise feedbacks.temp("Max attributes reached")
            
            for syn in (name, *aliases):
                if len(syn) > attributes.MAX_SYN_LEN:
                    raise feedbacks.temp("Max syn length exceeded")
                
                if self.get_any_attribute_by_syn(syn) is not None:
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
                c.execute(lambda arg: f"""
                    INSERT INTO {AttributeTbl} (
                        {AttributeTbl.list_id},
                        {AttributeTbl.name},
                        {AttributeTbl.slot_type},
                        {AttributeTbl.position},
                        {AttributeTbl.min_slots},
                        {AttributeTbl.max_slots},
                        {AttributeTbl.uniqueness},
                    )
                    VALUES (
                        {arg(self.id)},
                        {arg(name)},
                        {arg(value_type.id)},
                        {arg(index)},
                        {arg(min_slots)},
                        {arg(max_slots)},
                        {arg(uniqueness.value)},
                    )
                """)

                attribute_id = c.last_generated_id

                if aliases:
                    AttributeAliasTbl = type.tables.attribute_alias

                    c.execute(lambda arg: f"""
                        INSERT INTO {AttributeAliasTbl} (
                            {AttributeAliasTbl.attribute_id},
                            {AttributeAliasTbl.list_id},
                            {AttributeAliasTbl.alias}
                        ) 
                        VALUES 
                            {','.join(f"""(
                                {arg(attribute_id)}, 
                                {arg(self.id)}, 
                                {arg(alias)})""" 
                            for alias in aliases)}
                    """)

                attribute = type(
                    list=self,
                    id=attribute_id,
                    name=name,
                    slot_type=value_type,
                    position=index,
                    min_slots=min_slots,
                    max_slots=max_slots,
                    uniqueness=uniqueness
                )

                if top_raw_nodes:
                    if not isinstance(attribute, BaseNonStaticAttribute):
                        raise feedbacks.temp("Not CollectionAttribute")
                    
                    attribute.set_collection(top_raw_nodes)
                    
                return attribute

    def delete_attribute[T: BaseAttribute](self, type: type[T], attribute_id: int) -> bool:
        AttributeTbl = type.tables.attribute

        with self.locked, queries.connected() as c:
            c.execute(lambda arg: f"""
                DELETE FROM {AttributeTbl}
                WHERE {AttributeTbl.list_id} = {arg(self.id)}
                AND {AttributeTbl.id} = {arg(attribute_id)}
            """)

            return c.affected_row_count > 0

    # --- Tasks ---

    def _raw_attribute_value_mapping_to_non_raw(
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
        
        # Check if slot is unique per entire list
        unique_per_list_attrs = {
            attr for attr in attribute_value_mapping
            if attr.uniqueness >= Uniqueness.PER_ATTRIBUTE
        }

        if unique_per_list_attrs:
            TaskValueTbl = typed.TaskAttributeTaskValueNotUnique

            with queries.connected() as c:
                c.execute(lambda arg: f"""
                    SELECT 
                        {TaskValueTbl.value},
                        {TaskValueTbl.attribute_id}
                    FROM {TaskValueTbl}
                    WHERE 
                        {TaskValueTbl.attribute_id} in (
                            {','.join(arg(attr.id) for attr in unique_per_list_attrs)}
                        )
                """)

                rows = c.fetchall(TaskValueTbl)

            attr_id_to_all_slots: dict[int, set[SlotTypeT]] = {
                attr.id: set() for attr in unique_per_list_attrs
            }

            #dont forget to norm
            for row in rows:
                slots: list[SlotTypeT] = pickle.loads(row.value)
                attr_id = row.attribute_id

                attr_id_to_all_slots[attr_id].update(slots)

            for attr in unique_per_list_attrs:
                for 
                

                


        return attribute_value_mapping
    

    def create_task(
        self, 
        name: str, 
        aliases: frozenset[str], 
        raw_attribute_value_mapping: dict[int, AttributeValueParseTypesT]
    ) -> Task:
        with self.locked:
            if len(self.get_tasks()) >= list_package.MAX_TASKS:
                raise feedbacks.temp("Task limit reached")
            
            for syn in (name, *aliases):
                if self.get_task_by_syn(syn) is not None:
                    raise feedbacks.temp(f"Task with name or alias {syn} already exists")
            
            attribute_value_mapping = self._raw_attribute_value_mapping_to_non_raw(raw_attribute_value_mapping)
                
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

                task_id = c.last_generated_id 
                
                if aliases:
                    c.execute(lambda arg: f"""
                        INSERT INTO {typed.TaskAlias} (
                            {typed.TaskAlias.task_id},
                            {typed.TaskAlias.list_id},
                            {typed.TaskAlias.alias}
                        ) 
                        VALUES 
                            {','.join(f"""(
                                {arg(task_id)}, 
                                {arg(self.id)}, 
                                {arg(alias)})
                            """ for alias in aliases)}        
                    """)

                if attribute_value_mapping:
                    TaskValueTbl = TaskAttribute.tables.attribute_task_value
                    
                    c.execute(lambda arg: f"""
                        INSERT INTO {TaskValueTbl} (
                            {TaskValueTbl.task_id},
                            {TaskValueTbl.attribute_id},
                            {TaskValueTbl.value}
                        )
                        VALUES 
                            {','.join(f"""(
                                {arg(task_id)}, 
                                {arg(attr.id)}, 
                                {arg(pickle.dumps(v))})
                            """ for attr, v in attribute_value_mapping.items())}
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
        
    def edit_task(self, id: int, name: str | None = None, aliases: frozenset[str] | None = None, raw_attribute_value_mapping):
        with self.locked:
            
        
    def _fetch_tasks_from_table(self, where: Callable[[Arg], str] | None) -> Rows[typed.Task]:
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
            id=row.id,
            name=row.name
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
            c.execute(lambda arg: f"""
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