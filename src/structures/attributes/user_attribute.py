

from dataclasses import dataclass, field
import json
from typing import ClassVar
from database import queries
from database.typed import Tables as Tables
from database import typed
from structures import attributes
from structures.attributes import AttributeDataCache, RawCollectionNodesT, SlotTypeT
from structures.attributes import collection
from structures.attributes.base_attribute import BaseAttribute
from structures.attributes.collection import Collection


@dataclass(frozen=True, kw_only=True)
class UserAttribute[T: SlotTypeT](BaseAttribute[T]):
    __structure_name__ = 'user attribute'


    def get_collection(self) -> Collection[T]:
        if self._cache.collection is None:
            self._cache.collection = attributes.get_collection_helper(self)

        return self._cache.collection
    
    def set_collection(self, top_raw_nodes: RawCollectionNodesT[T]) -> Collection[T]:
        with self.locked:
            if self._cache.collection is None:
                self._cache.collection = attributes.set_collection_helper(top_raw_nodes, self)
            
            return self._cache.collection