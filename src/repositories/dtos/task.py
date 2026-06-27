


from dataclasses import dataclass

from domain.types.list import ListID
from domain.types.task import TaskID
from domain.value_objects.task_attribute_slot import TaskAttributeSlot


@dataclass(frozen=True, slots=True)
class TaskInsert:
    list_id: ListID
    name: TaskAttributeSlot

@dataclass(frozen=True, slots=True)
class TaskAliasInsert:
    task_id: TaskID
    list_id: ListID
    alias: TaskAttributeSlot