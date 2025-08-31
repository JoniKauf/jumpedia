
from dataclasses import dataclass
from database import typed
from structures.attributes import BaseNonStaticAttribute, SlotTypeT
from structures.attributes import BaseNonStaticAttributeTables


@dataclass(frozen=True, kw_only=True)
class TaskAttribute[T: SlotTypeT](BaseNonStaticAttribute[T]):
    __structure_name__ = 'task attribute'
    tables = BaseNonStaticAttributeTables(
        typed.TaskAttribute,
        typed.TaskAttributeAlias,
        typed.TaskAttributeCollectionSlot,
        typed.TaskAttributeCollectionSlotAlias,
        typed.TaskAttributeTaskValue
    )