from dataclasses import dataclass, field
import pickle
from typing import TYPE_CHECKING, TypedDict

from database import queries
from database import typed
from database.typed import Tables as Tables

from errors.feedback import feedbacks
from structures.base_structure import BaseStructure
from structures.attributes import AnyAttributeT, AttributeValueTypeT
from structures.attributes.static_attribute import StaticAttribute
from structures.attributes.task_attribute import TaskAttribute
from structures.attributes.user_attribute import UserAttribute
from structures.task import Task

@dataclass(frozen=True, kw_only=True)
class AbstractAttributeValueMapping[T: AnyAttributeT](BaseStructure):
    task: 'Task'
    mapping: dict[T, list[AttributeValueTypeT]] = field(init=False, default_factory=dict)

    @property
    def sorted_attributes(self) -> list[T]:
        return [
            attr for attr in sorted(
                self.mapping, key=lambda a: a.position
            )
        ]
    
    @property
    def sorted_values(self) -> list[list['AttributeValueTypeT']]:
        return [
            v for _, v in (
                sorted(self.mapping.items(), key=lambda item: item[0].position)
            )
        ]
    
    @property
    def sorted_items(self) -> list[tuple[T, list['AttributeValueTypeT']]]:
        return [
            (attr, v) for attr, v in (
                sorted(self.mapping.items(), key=lambda item: item[0].position)
            )
        ]
    
    @property
    def identity(self) -> tuple[int, ...]:
        return self.task.identity
    
    def __post_init__(self) -> None:
        if self.__class__ == AbstractAttributeValueMapping:
            raise NotImplementedError()
        
        self._add_static_attributes()
        self._add_task_attributes()
    
    def _add_static_attributes(self) -> None:
        for attr in self.task.list.get_static_attributes():
            self.mapping[attr] = attr.get_value(self.task)  # type: ignore
    
    def _add_task_attributes(self) -> None:
        h = queries.ArgHelper()

        with queries.connected() as (conn, cursor):
            cursor.execute(f"""
                SELECT *
                FROM {Tables.TaskAttributeTaskValue}
                WHERE {Tables.TaskAttributeTaskValue.task_id} = {h|self.task.id}
            """, h.steal())

            result: typed.ManyTableRowT = cursor.fetchall()

        task_attribute_ids: tuple[int, ...] = tuple(
            row[Tables.TaskAttributeTaskValue.task_attribute_id] for row in result
        )
        
        # Get all attributes specified for this task
        attributes = self.task.list.get_task_attributes(
            lambda h: f"{Tables.TaskAttribute.id} in ({','.join((h|attr) for attr in task_attribute_ids)})"
        )

        attribute_lookup: dict[int, TaskAttribute] = {
            attr.id: attr for attr in attributes
        }
        
        for row in result:
            try:
                attr = attribute_lookup.pop(row['task_attribute_id'])
            except KeyError:
                raise feedbacks.temp("Data changed")
            
            val: list[AttributeValueTypeT] = pickle.loads(row['value'])
            
            self.mapping[attr] = val  # type: ignore

        if attribute_lookup:
            raise feedbacks.temp("Data changed")


