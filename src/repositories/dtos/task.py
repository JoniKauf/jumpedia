


from dataclasses import dataclass

from domain.types.list import ListID
from domain.value_objects.task_value_slot import TaskValueSlot


@dataclass(frozen=True, slots=True)
class TaskInsert:
    list_id: ListID
    name: TaskValueSlot