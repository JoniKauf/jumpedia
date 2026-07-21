from dataclasses import dataclass

from domain.typing.attribute import AttributeID
from domain.typing.task import TaskID
from domain.value_objects.field_slot import FieldSlotStr
from domain.value_objects.index import Index


@dataclass(frozen=True, slots=True)
class FieldSlotInsert:
    task_id: TaskID
    attribute_id: AttributeID
    index: Index
    slot: FieldSlotStr
