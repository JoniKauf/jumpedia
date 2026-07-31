from jumpedia.domain.entities.base import BaseEntity
from jumpedia.domain.typing.attribute import AttributeID
from jumpedia.domain.typing.member_task import MemberTaskID

lazy from jumpedia.domain.value_objects.field_slot import FieldSlotStr
from dataclasses import dataclass

from jumpedia.domain.value_objects.index import Index


@dataclass(frozen=True, slots=True)
class MemberFieldSlotEntity(BaseEntity[MemberTaskID, AttributeID, Index]):
    slot: FieldSlotStr

    @property
    def member_task_id(self) -> MemberTaskID:
        return self.key[0]

    @property
    def attribute_id(self) -> AttributeID:
        return self.key[1]

    @property
    def index(self) -> Index:
        return self.key[2]
