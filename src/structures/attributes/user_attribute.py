

from dataclasses import dataclass
from typing import ClassVar
from database import typed
from structures.attributes import BaseNonStaticAttribute, SlotTypeT
from structures.attributes import BaseNonStaticAttributeTables


@dataclass(frozen=True, kw_only=True)
class UserAttribute[T: SlotTypeT](BaseNonStaticAttribute[T]):
    __structure_name__: ClassVar = 'user attribute'
    tables = BaseNonStaticAttributeTables(
        typed.UserAttribute,
        typed.UserAttributeAlias,
        typed.UserAttributeCollectionSlot,
        typed.UserAttributeCollectionSlotAlias,
        typed.UserAttributeTaskValue
    )