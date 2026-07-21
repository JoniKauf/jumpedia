from dataclasses import dataclass

from domain.typing.list import ListID
from domain.typing.task import TaskID
from domain.value_objects.field_slot import FieldSlotStr
from domain.value_objects.index import Index


@dataclass(frozen=True, slots=True)
class TaskInsert:
    list_id: ListID
    name: FieldSlotStr


@dataclass(frozen=True, slots=True)
class TaskAliasInsert:
    task_id: TaskID
    index: Index
    list_id: ListID
    alias: FieldSlotStr
