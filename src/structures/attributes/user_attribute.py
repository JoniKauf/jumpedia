

from dataclasses import dataclass
from typing import ClassVar
from database import typed
from structures.attributes import SlotTypeT, Uniqueness
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

    def __post_init__(self) -> None:
        if self.uniqueness >= Uniqueness.PER_LIST:
            raise RuntimeError()
        
        return super().__post_init__()