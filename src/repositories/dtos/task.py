from dataclasses import dataclass

from domain.types.list import ListID
from domain.types.task import TaskID
from domain.value_objects.index import Index
from domain.value_objects.task_attribute_slot import TaskAttributeSlotStr


@dataclass(frozen=True, slots=True)
class TaskInsert:
    list_id: ListID
    name: TaskAttributeSlotStr


@dataclass(frozen=True, slots=True)
class TaskAliasInsert:
    task_id: TaskID
    index: Index
    list_id: ListID
    alias: TaskAttributeSlotStr
