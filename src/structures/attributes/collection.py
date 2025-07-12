

from dataclasses import dataclass, field
import json
import pickle
from types import MappingProxyType
from typing import Any, Iterable, Self, Sequence, overload
from structures.attributes import AnyAttributeT, AttributeValueType, AttributeValueTypeT, CollectionAttributeT
from database import typed
from database.typed import Tables as TBL
from structures.attributes.static_attribute import StaticAttribute
from structures.base_structure import BaseStructure
from utils import text
from database import dbutils

from structures.attributes.task_attribute import TaskAttribute
from structures.attributes.user_attribute import UserAttribute

type CollectionNodesT[T: AttributeValueTypeT] = frozenset[CollectionNode[T]]

@dataclass(frozen=True)
class CollectionNode[T: AttributeValueTypeT]:
    value: T
    aliases: frozenset[T]
    sort_value: int
    children: CollectionNodesT[T]
    parent: 'CollectionNode[T] | None'
    value_type: AttributeValueType[T]

    def __hash__(self) -> int:
        return hash(self.value_type.norm(self.value))
    
    def __eq__(self, other: object) -> bool:
        if isinstance(other, type(self)):
            return self.value_type.norm(self.value) == self.value_type.norm(other.value)

        return NotImplemented
    
    def _post_set_children(self, children: 'CollectionNodesT[T]') -> None:
        object.__setattr__(self, 'children', children)


_MISSING = object()

@dataclass(frozen=True, kw_only=True)
class Collection[T: AttributeValueTypeT](BaseStructure):
    # We support StaticAttribute for empty(), but other methods only work without StaticAttribute
    attribute: AnyAttributeT[T]
    top_nodes: CollectionNodesT[T]
    normed_node_value_to_node: MappingProxyType[T, CollectionNode[T]]

    @property
    def identity(self) -> tuple[int, ...]:
        return (0, *self.attribute.identity)
    
    @property
    def all_nodes(self) -> tuple[CollectionNode[T], ...]:
        return tuple(self.normed_node_value_to_node.values())
    
    
    @overload
    def lookup_node(self, value: T) -> CollectionNode[T]: 
        ...
    
    @overload
    def lookup_node[TDefault: Any](self, value: T, default: TDefault) -> CollectionNode[T] | TDefault: 
        ...

    def lookup_node(self, value: T, default: Any = _MISSING) -> Any:
        value = self.attribute.value_type.norm(value)

        if default is _MISSING:
            return self.normed_node_value_to_node[value]
        
        return self.normed_node_value_to_node.get(value, default)
