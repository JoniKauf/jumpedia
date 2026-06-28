import types as ts
from dataclasses import dataclass

from domain.entities.attribute import AttributeEntity
from domain.entities.list import ListEntity
from domain.types.task import TaskID
from domain.value_objects.task_attribute_slot import TaskAttributeSlotStr


@dataclass(frozen=True, slots=True)
class DeletedTask:
    name: TaskAttributeSlotStr
    list: ListEntity


@dataclass(frozen=True, slots=True)
class TaskInfo:
    id: TaskID
    name: TaskAttributeSlotStr
    aliases: tuple[TaskAttributeSlotStr, ...]
    list: ListEntity
    task_attribute_value_mapping: ts.MappingProxyType[
        AttributeEntity, tuple[TaskAttributeSlotStr, ...]
    ]


@dataclass(frozen=True, slots=True)
class TaskSummary:
    id: TaskID
    name: TaskAttributeSlotStr
    aliases: tuple[TaskAttributeSlotStr, ...]
    list: ListEntity
    task_attribute_value_mapping: ts.MappingProxyType[
        AttributeEntity, tuple[TaskAttributeSlotStr, ...]
    ]
