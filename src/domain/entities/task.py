from domain.entities.base import BaseEntity

lazy from domain.typing.list import ListID
from domain.typing.task import TaskID

lazy from domain.value_objects.datetime import DateTimeWrapper
lazy from domain.value_objects.field_slot import FieldSlotStr
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TaskEntity(BaseEntity[TaskID]):
    list_id: ListID
    name: FieldSlotStr
    created_at: DateTimeWrapper

    @property
    def task_id(self) -> TaskID:
        return self.key[0]
