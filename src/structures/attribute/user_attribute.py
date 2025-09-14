

from dataclasses import dataclass
from typing import ClassVar
from database import typed
from structures.attribute import BaseNonStaticAttribute, SlotTypeT
from structures.attribute import BaseNonStaticAttributeTables


@dataclass(frozen=True, kw_only=True)
class UserAttribute[T: SlotTypeT](BaseNonStaticAttribute[T]):
    tables = BaseNonStaticAttributeTables(
        typed.UserAttribute,
        typed.UserAttributeAlias,
        typed.UserAttributeCollectionSlot,
        typed.UserAttributeCollectionSlotAlias,
        typed.UserAttributeTaskValue
    )