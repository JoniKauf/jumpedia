from dataclasses import dataclass

from database import typed
from structures.attributes import AttributeTables, SlotTypeT, Uniqueness
from structures.attributes import BaseAttribute

@dataclass(frozen=True, kw_only=True)
class StaticAttribute[T: SlotTypeT](BaseAttribute[T]):
    __structure_name__ = "static attribute"
    tables = AttributeTables(
        typed.StaticAttribute,
        typed.StaticAttributeAlias
    )
    allow_min_slots_on_creation = True
    deletable = False