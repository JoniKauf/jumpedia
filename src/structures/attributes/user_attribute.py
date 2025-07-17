

from dataclasses import dataclass
from typing import ClassVar
from database import typed
from structures.attributes import SlotTypeT
from structures.attributes.collection import BaseCollectionAttribute, CollectionAttributeTables


@dataclass(frozen=True, kw_only=True)
class UserAttribute[T: SlotTypeT](BaseCollectionAttribute[T]):
    __structure_name__: ClassVar = 'user attribute'
    tables = CollectionAttributeTables(
        typed.UserAttribute,
        typed.UserAttributeAlias,
        typed.UserAttributeTaskValue,
        typed.UserAttributeCollectionNode,
        typed.UserAttributeCollectionNodeAlias
    )