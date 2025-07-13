

from dataclasses import dataclass, field
import json
import pickle
from types import MappingProxyType
from typing import Any, Final, Iterable, Self, Sequence, overload
from structures.attributes import AnyAttributeT, CollectionAttributeT
from database import typed
from database.typed import Tables as Tables
from structures.attributes.base_attribute import BaseAttribute
from structures.attributes.slot_type import SlotType, SlotTypeT
from structures.attributes.static_attribute import StaticAttribute
from structures.base_structure import BaseStructure
from utils import text
from database import dbutils

from structures.attributes.task_attribute import TaskAttribute
from structures.attributes.user_attribute import UserAttribute


# Collection
MAX_ELEMS: Final[int] = 1024
MAX_DEPTH: Final[int] = 16


type CollectionNodesT[T: SlotTypeT] = frozenset[CollectionNode[T]]

@dataclass(frozen=True)
class CollectionNode[T: SlotTypeT]:
    value: T
    aliases: frozenset[T]
    sort_value: int
    parent: 'CollectionNode[T] | None'
    children: CollectionNodesT[T]
    slot_type: SlotType[T]

    def __hash__(self) -> int:
        return hash(self.slot_type.norm(self.value))
    
    def __eq__(self, other: object) -> bool:
        if isinstance(other, type(self)):
            return self.slot_type.norm(self.value) == self.slot_type.norm(other.value)

        return NotImplemented
    
    def _post_set_children(self, children: 'CollectionNodesT[T]') -> None:
        """Set the children field of the node.
        
        It is logically impossible to set both parent and children at
        construction time for a whole tree. Therefore we allow the 
        exception to postpone setting the children field.
        """
        object.__setattr__(self, 'children', children)


_MISSING = object()

@dataclass(frozen=True, kw_only=True)
class Collection[T: SlotTypeT](BaseStructure):
    # We support StaticAttribute for empty(), but other methods only work without StaticAttribute
    attribute: BaseAttribute[T]
    top_nodes: CollectionNodesT[T]
    normed_syn_to_node: MappingProxyType[T, CollectionNode[T]]

    @property
    def identity(self) -> tuple[int, ...]:
        return (0, *self.attribute.identity)
    
    @property
    def all_nodes(self) -> frozenset[CollectionNode[T]]:
        return frozenset(self.normed_syn_to_node.values())
    
    @property
    def is_empty(self) -> bool:
        return bool(self.top_nodes)
    
    @overload
    def lookup_node(self, syn: T) -> CollectionNode[T]: 
        ...
    
    @overload
    def lookup_node[TDefault: Any](self, syn: T, default: TDefault) -> CollectionNode[T] | TDefault: 
        ...

    def lookup_node(self, syn: T, default: Any = _MISSING) -> Any:
        syn = self.attribute.slot_type.norm(syn)

        if default is _MISSING:
            return self.normed_syn_to_node[syn]
        
        return self.normed_syn_to_node.get(syn, default)