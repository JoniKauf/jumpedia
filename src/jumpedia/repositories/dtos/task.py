from dataclasses import dataclass

from jumpedia.domain.typing.list import ListID
from jumpedia.domain.typing.task import TaskID
from jumpedia.domain.value_objects.field_slot import FieldSlotStr
from jumpedia.domain.value_objects.index import Index


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
