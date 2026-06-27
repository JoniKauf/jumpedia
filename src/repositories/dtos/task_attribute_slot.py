from dataclasses import dataclass

from domain.types.attribute import AttributeID
from domain.types.task import TaskID
from domain.value_objects.index import Index
from domain.value_objects.task_attribute_slot import TaskAttributeSlot


@dataclass(frozen=True, slots=True)
class TaskAttributeSlotInsert:
    task_id: TaskID
    attribute_id: AttributeID
    index: Index
    slot: TaskAttributeSlot