from domain.entities.base import BaseEntity
from domain.types.list import ListID
from domain.types.task import TaskID
from domain.value_objects.field_slot import FieldSlotStr


class TaskEntity(BaseEntity[TaskID]):
    def __init__(self, task_id: TaskID, list_id: ListID, name: FieldSlotStr) -> None:
        super().__init__(task_id)
        self._list_id = list_id
        self.name = name

    @property
    def task_id(self) -> TaskID:
        return self._composite_key[0]

    @property
    def list_id(self) -> ListID:
        return self._list_id

    @property
    def name(self) -> FieldSlotStr:
        return self._name

    @name.setter
    def name(self, value: FieldSlotStr) -> None:
        self._name = value
