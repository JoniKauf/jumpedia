from dataclasses import dataclass

from jumpedia.domain.typing.attribute import AttributeID
from jumpedia.domain.typing.member_task import MemberTaskID
from jumpedia.domain.value_objects.field_slot import FieldSlotStr
from jumpedia.domain.value_objects.index import Index


@dataclass(frozen=True, slots=True)
class MemberFieldSlotInsert:
    member_task_id: MemberTaskID
    attribute_id: AttributeID
    index: Index
    slot: FieldSlotStr
