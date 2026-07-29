from domain.entities.base import BaseEntity
from domain.typing.attribute import AttributeID
from domain.typing.task import TaskID

lazy from domain.value_objects.field_slot import FieldSlotStr
from dataclasses import dataclass

from domain.value_objects.index import Index


@dataclass(frozen=True, slots=True)
class FieldSlotEntity(BaseEntity[TaskID, AttributeID, Index]):
    slot: FieldSlotStr

    @property
    def task_id(self) -> TaskID:
        return self.key[0]

    @property
    def attribute_id(self) -> AttributeID:
        return self.key[1]

    @property
    def index(self) -> Index:
        return self.key[2]
