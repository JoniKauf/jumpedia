

from dataclasses import InitVar, dataclass

from domain.enums.attribute import SlotType
import typing as t

from domain.value_objects.limits import Limits

@dataclass(frozen=True, unsafe_hash=True, slots=True)
class Slot:
    type: SlotType
    min_count: int
    max_count: int
    limits: Limits

    def __post_init__(self) -> None:
        if not (
            Limits.ATTRIBUTE_TASK_VALUE_MIN_MIN_SLOT_COUNT <= self.min_count <= self.max_count <= self.limits.attribute_task_value_slot_count_max
            and self.max_count >= Limits.ATTRIBUTE_TASK_VALUE_MIN_MAX_SLOT_COUNT 
        ):
            raise ValueError("Invalid slot bounds", self.min_count, self.max_count)
            
    
