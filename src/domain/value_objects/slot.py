

from dataclasses import dataclass

from domain.enums.attribute import SlotType
import typing as t

@dataclass(frozen=True, unsafe_hash=True, slots=True)
class Slot:
    type: SlotType
    min_count: int
    max_count: int

    def __post_init__(self) -> None:
        if not (
            Slot.MIN_MIN_COUNT <= self.min_count <= self.max_count <= Slot.MAX_MAX_COUNT 
            and self.max_count >= Slot.MIN_MAX_COUNT
        ):
            raise ValueError("Invalid slot bounds", self.min_count, self.max_count)
            
    MIN_MIN_COUNT: t.ClassVar[t.Final[int]] = 0
    MIN_MAX_COUNT: t.ClassVar[t.Final[int]] = 1
    MAX_MAX_COUNT: t.ClassVar[t.Final[int]] = 32
