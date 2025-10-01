from dataclasses import dataclass
from database import typed
from structures.attribute import BaseNonStaticAttribute
from structures.attribute import BaseNonStaticAttributeTables


class TaskAttribute(BaseNonStaticAttribute):
    tables = BaseNonStaticAttributeTables(
        typed.TaskAttribute,
        typed.TaskAttributeAlias,
        typed.TaskAttributeCollectionSlot,
        typed.TaskAttributeCollectionSlotAlias,
        typed.TaskAttributeTaskValue,
    )
