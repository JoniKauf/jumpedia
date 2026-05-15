from dataclasses import dataclass
from domain.value_objects.slot import Slot
from domain.value_objects.strings import StrStore

from domain.enums.attribute import Kind, Type

# TODO MAKE BaseEntity used for others
@dataclass(frozen=True, unsafe_hash=True, slots=True)
class AttributeEntity:
    attribute_id: int
    list_id: int
    type: Type
    kind: Kind
    name: StrStore
    slot: Slot
    position: int

    def __post_init__(self) -> None:
        if self.position < 1:
            raise ValueError("position < 1")