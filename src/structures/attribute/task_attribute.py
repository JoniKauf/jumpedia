
from dataclasses import dataclass
from database import typed
from structures.attribute import BaseNonStaticAttribute, SlotTypeT
from structures.attribute import BaseNonStaticAttributeTables


@dataclass(frozen=True, kw_only=True)
class TaskAttribute(BaseNonStaticAttribute):
    tables = BaseNonStaticAttributeTables(
        typed.TaskAttribute,
        typed.TaskAttributeAlias,
        typed.TaskAttributeCollectionSlot,
        typed.TaskAttributeCollectionSlotAlias,
        typed.TaskAttributeTaskValue
    )