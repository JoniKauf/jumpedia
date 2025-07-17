

from dataclasses import dataclass, field
import json
from typing import ClassVar
from database import layout, queries
from structures import attributes
from structures.attributes import AttributeDataCache, RawCollectionNodesT, SlotTypeT
from structures.attributes import collection
from structures.attributes import BaseAttribute
from structures.attributes.collection import AttributeTablesWithCollection, BaseCollectionAttribute, Collection


@dataclass(frozen=True, kw_only=True)
class UserAttribute[T: SlotTypeT](BaseCollectionAttribute[
    T, 
    layout.UserAttribute,
    layout.UserAttributeAlias,
    layout.UserAttributeTaskValue,
    layout.UserAttributeCollectionNode,
    layout.UserAttributeCollectionNodeAlias
]):
    __structure_name__: ClassVar = 'user attribute'
    
    @staticmethod
    def tables():
        return AttributeTablesWithCollection(
            layout.UserAttribute,
            layout.UserAttributeAlias,
            layout.UserAttributeTaskValue,
            layout.UserAttributeCollectionNode,
            layout.UserAttributeCollectionNodeAlias
        )

    def get_collection(self) -> Collection[T]:
        if self._cache.collection is None:
            self._cache.collection = attributes.get_collection_helper(self)

        return self._cache.collection
    
    def set_collection(self, top_raw_nodes: RawCollectionNodesT[T]) -> Collection[T]:
        with self.locked:
            if self._cache.collection is None:
                self._cache.collection = attributes.set_collection_helper(top_raw_nodes, self)
            
            return self._cache.collection