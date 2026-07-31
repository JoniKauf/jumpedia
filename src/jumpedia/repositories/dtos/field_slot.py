from dataclasses import dataclass

from jumpedia.domain.typing.attribute import AttributeID
from jumpedia.domain.typing.task import TaskID
from jumpedia.domain.value_objects.field_slot import FieldSlotStr
from jumpedia.domain.value_objects.index import Index


@dataclass(frozen=True, slots=True)
class FieldSlotInsert:
    task_id: TaskID
    attribute_id: AttributeID
    index: Index
    slot: FieldSlotStr
