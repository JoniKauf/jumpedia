from typing import Any

from domain.entities.base import BaseEntity
from domain.types.attribute import AttributeID
from domain.types.task import TaskID
from domain.value_objects.index import Index
from domain.value_objects.task_attribute_slot import TaskAttributeSlotStr


class TaskAttributeSlotEntity(BaseEntity[TaskID, AttributeID, Index]):
    def __init__(
        self,
        task_id: TaskID,
        attribute_id: AttributeID,
        index: Index,
        slot: TaskAttributeSlotStr,
    ) -> None:
        super().__init__(task_id, attribute_id, index)

        self.slot = slot

    @property
    def task_id(self) -> TaskID:
        return self._composite_key[0]

    @property
    def attribute_id(self) -> AttributeID:
        return self._composite_key[1]

    @property
    def index(self) -> Index:
        return self._composite_key[2]

    @property
    def slot(self) -> TaskAttributeSlotStr:
        return self._slot

    @slot.setter
    def slot(self, value: TaskAttributeSlotStr) -> None:
        self._slot = value
