
from dataclasses import dataclass, field
import json
from types import MappingProxyType
from typing import ClassVar, Self

from database import queries
from database.typed import Tables as Tables
from database import typed
from errors.feedback import feedbacks
from structures import attributes
from structures.attributes import AttributeDataCache, SlotTypeT, RawCollectionNode, RawCollectionNodesT, UniquenessExtended
from structures.attributes.base_attribute import BaseAttribute
from structures.attributes.collection import Collection, CollectionNode, CollectionNodesT
from structures.attributes import collection
from utils import parsetools


@dataclass(frozen=True, kw_only=True)
class TaskAttribute[T: SlotTypeT](BaseAttribute[T]):
    __structure_name__ = 'task attribute'

    uniqueness: UniquenessExtended

    def get_collection(self) -> Collection[T]:
        if self._cache.collection is None:
            self._cache.collection = attributes.get_collection_helper(self)

        return self._cache.collection
    
    def set_collection(self, top_raw_nodes: RawCollectionNodesT[T]) -> Collection[T]:
        with self.locked:
            if self._cache.collection is None:
                self._cache.collection = attributes.set_collection_helper(top_raw_nodes, self)
            
            return self._cache.collection