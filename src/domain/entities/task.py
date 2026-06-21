


from domain.entities.base import BaseEntity
from domain.types.list import ListID
from domain.types.task import TaskID
from domain.value_objects.task_value_slot import TaskValueSlot


class TaskEntity(BaseEntity[TaskID]):
    def __init__(self, id: TaskID, list_id: ListID, name: TaskValueSlot) -> None:
        super().__init__(id)
        self._list_id = list_id
        self.name = name

    @property
    def list_id(self) -> ListID:
        return self._list_id
    
    @property
    def name(self) -> TaskValueSlot:
        return self._name
    
    @name.setter
    def name(self, value: TaskValueSlot) -> None:
        self._name = value