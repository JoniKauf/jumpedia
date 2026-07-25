from domain.entities.base import BaseEntity

lazy from domain.typing.list import ListID
from domain.typing.task import TaskID

lazy from domain.value_objects.datetime import DateTimeWrapper
lazy from domain.value_objects.field_slot import FieldSlotStr


class TaskEntity(BaseEntity[TaskID]):
    def __init__(
        self,
        task_id: TaskID,
        list_id: ListID,
        name: FieldSlotStr,
        created_at: DateTimeWrapper,
    ) -> None:
        super().__init__(task_id)
        self._list_id = list_id
        self.name = name
        self._created_at = created_at

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

    @property
    def created_at(self) -> DateTimeWrapper:
        return self._created_at
