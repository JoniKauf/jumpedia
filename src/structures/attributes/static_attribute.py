from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, ClassVar

from database import layout, queries
from database import typed
from database.typed import Tables

from errors import ImpossibleError
from structures import attributes
from structures.attributes import AttributeDataCache, AttributeTables, SlotTypeT, RawCollectionNode, RawCollectionNodesT, UniquenessExtended
from structures.attributes import BaseAttribute
from structures.attributes.collection import Collection

@dataclass(frozen=True, kw_only=True)
class StaticAttribute[T: SlotTypeT](BaseAttribute[T]):
    __structure_name__ = "static attribute"
    tables = AttributeTables(
        layout.StaticAttribute,
        layout.StaticAttributeAlias,
        layout.StaticAttributeTaskValue
    )

    uniqueness: UniquenessExtended

    def get_collection(self) -> Collection[T]:
        return Collection(
            attribute=self,
            top_nodes=frozenset(),
            normed_syn_to_node=MappingProxyType({})
        )
    