from dataclasses import dataclass

from domain.types.attribute import AttributeID
from domain.types.task import TaskID
from domain.value_objects.index import Index
from domain.value_objects.field_slot import FieldSlotStr


@dataclass(frozen=True, slots=True)
class FieldSlotInsert:
    task_id: TaskID
    attribute_id: AttributeID
    index: Index
    slot: FieldSlotStr
