from dataclasses import dataclass

from domain.typing.attribute import AttributeID
from domain.typing.member_task import MemberTaskID
from domain.value_objects.field_slot import FieldSlotStr
from domain.value_objects.index import Index


@dataclass(frozen=True, slots=True)
class MemberFieldSlotInsert:
    member_task_id: MemberTaskID
    attribute_id: AttributeID
    index: Index
    slot: FieldSlotStr
