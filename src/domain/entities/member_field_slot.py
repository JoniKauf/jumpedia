from typing import Any

from domain.entities.base import BaseEntity
from domain.typing.attribute import AttributeID
from domain.typing.member_task import MemberTaskID
from domain.typing.task import TaskID
from domain.value_objects.field_slot import FieldSlotStr
from domain.value_objects.index import Index


class MemberFieldSlotEntity(BaseEntity[MemberTaskID, AttributeID, Index]):
    def __init__(
        self,
        member_task_id: MemberTaskID,
        attribute_id: AttributeID,
        index: Index,
        slot: FieldSlotStr,
    ) -> None:
        super().__init__(member_task_id, attribute_id, index)
        self.slot = slot

    @property
    def member_task_id(self) -> MemberTaskID:
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
