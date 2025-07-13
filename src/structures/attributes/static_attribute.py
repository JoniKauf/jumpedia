from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, ClassVar

from database import queries
from database import typed
from database.typed import Tables

from errors import ImpossibleError
from structures import attributes
from structures.attributes import AttributeDataCache, SlotTypeT, RawCollectionNode, RawCollectionNodesT, UniquenessExtended
from structures.attributes.base_attribute import BaseAttribute
from structures.attributes.collection import Collection

@dataclass(frozen=True, kw_only=True)
class StaticAttribute[T: SlotTypeT](BaseAttribute[T]):
    __structure_name__ = "static attribute"

    uniqueness: UniquenessExtended

    def get_collection(self) -> Collection[T]:
        return Collection(
            attribute=self,
            top_nodes=frozenset(),
            normed_syn_to_node=MappingProxyType({})
        )
    