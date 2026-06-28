from domain.entities.base import BaseEntity
from domain.types.list import ListID
from domain.types.task import TaskID
from domain.value_objects.task_attribute_slot import TaskAttributeSlotStr


class TaskEntity(BaseEntity[TaskID]):
    def __init__(
        self, primary_key: TaskID, list_id: ListID, name: TaskAttributeSlotStr
    ) -> None:
        super().__init__(primary_key)
        self._list_id = list_id
        self.name = name

    @property
    def task_id(self) -> TaskID:
        return self._composite_key[0]

    @property
    def list_id(self) -> ListID:
        return self._list_id

    @property
    def name(self) -> TaskAttributeSlotStr:
        return self._name

    @name.setter
    def name(self, value: TaskAttributeSlotStr) -> None:
        self._name = value
