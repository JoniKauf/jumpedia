from typing import Any

from domain.entities.base import BaseEntity
from domain.types.attribute import AttributeID
from domain.types.task import TaskID
from domain.value_objects.index import Index
from domain.value_objects.field_slot import FieldSlotStr
from src.domain.types.user_task import UserTaskID


class UserFieldSlotEntity(BaseEntity[UserTaskID, AttributeID, Index]):
    def __init__(
        self,
        user_task_id: UserTaskID,
        attribute_id: AttributeID,
        index: Index,
        slot: FieldSlotStr,
    ) -> None:
        super().__init__(user_task_id, attribute_id, index)

        self.slot = slot

    @property
    def task_id(self) -> UserTaskID:
        return self._composite_key[0]

    @property
    def attribute_id(self) -> AttributeID:
        return self._composite_key[1]

    @property
    def index(self) -> Index:
        return self._composite_key[2]

    @property
    def slot(self) -> FieldSlotStr:
        return self._slot

    @slot.setter
    def slot(self, value: FieldSlotStr) -> None:
        self._slot = value
