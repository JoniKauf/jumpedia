

from abc import abstractmethod
from dataclasses import dataclass, field
import pickle
from types import MappingProxyType
from typing import Any, ClassVar, Final, Iterable, Protocol, Self, Sequence, overload
from errors.feedback import feedbacks
from structures.attributes import AnyAttributeT, AttributeTables, BaseAttribute, BaseNonStaticAttributeTables, RawCollectionNode, RawCollectionNodesT
from database import queries, typed
from structures.attributes.slot_type import SlotType, SlotTypeT
from structures.base_structure import BaseStructure
from utils import numbers

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