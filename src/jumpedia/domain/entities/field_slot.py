from jumpedia.domain.entities.base import BaseEntity
from jumpedia.domain.typing.attribute import AttributeID
from jumpedia.domain.typing.list import ListID
from jumpedia.domain.typing.task import TaskID

lazy from jumpedia.domain.value_objects.field_slot import FieldSlotStr
from dataclasses import dataclass

from jumpedia.domain.value_objects.index import Index


@dataclass(frozen=True, slots=True)
class FieldSlotEntity(BaseEntity[TaskID, AttributeID, Index]):
    list_id: ListID
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
