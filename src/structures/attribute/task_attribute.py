from dataclasses import dataclass

from ...database import typed
from . import BaseNonStaticAttribute, BaseNonStaticAttributeTables


class TaskAttribute(BaseNonStaticAttribute):
    tables = BaseNonStaticAttributeTables(
        typed.TaskAttribute,
        typed.TaskAttributeAlias,
        typed.TaskAttributeCollectionSlot,
        typed.TaskAttributeCollectionSlotAlias,
        typed.TaskAttributeTaskValue,
    )
    type_id = 1
