

from dataclasses import dataclass
import json
import pickle
from types import MappingProxyType
from typing import Any, Iterable, Self, Sequence, overload
from structures.attributes import AnyAttributeT, AttributeValueTypeT, CollectionAttributeT
from database import typed
from database.typed import Tables as TBL
from structures.attributes.static_attribute import StaticAttribute
from structures.base_structure import BaseStructure
from utils import text
from database import dbutils

from structures.attributes.task_attribute import TaskAttribute
from structures.attributes.user_attribute import UserAttribute

type CollectionNodesT[T: AttributeValueTypeT] = tuple[CollectionNode[T], ...]

@dataclass(frozen=True, unsafe_hash=True, eq=True)
class CollectionNode[T: AttributeValueTypeT]:
    id: int
    value: T
    aliases: frozenset[T]
    sort_value: int
    children: CollectionNodesT[T]
    root: 'CollectionNode[T] | None' = None

    def _post_set_children(self, children: 'CollectionNodesT[T]') -> None:
        object.__setattr__(self, 'children', children)


@dataclass(frozen=True)
class CollectionNodeRaw[T: AttributeValueTypeT]:
    id: int
    value: T
    aliases: frozenset[T]
    sort_value: int
    root_id: int | None


_MISSING = object()

@dataclass(frozen=True, kw_only=True)
class Collection[T: AttributeValueTypeT](BaseStructure):
    # We support StaticAttribute for empty(), but other methods only work without StaticAttribute
    attribute: AnyAttributeT[T]
    nodes: CollectionNodesT[T]
    normed_node_value_to_node: MappingProxyType[T, CollectionNode[T]]

    @property
    def identity(self) -> tuple[int, ...]:
        return (0, *self.attribute.identity)
    
    @overload
    @classmethod
    def create(cls, raw_nodes: tuple[()], attribute: StaticAttribute[T]) -> 'Collection[T]':
        pass

    @overload
    @classmethod
    def create(cls, raw_nodes: Sequence[CollectionNodeRaw[T]], attribute: CollectionAttributeT[T]) -> 'Collection[T]':
        pass

    @classmethod
    def create(cls, raw_nodes: Sequence[CollectionNodeRaw[T]], attribute: AnyAttributeT[T]) -> 'Collection[T]':
        if not raw_nodes:
            return cls(attribute=attribute, nodes=(), normed_node_value_to_node=MappingProxyType({}))
        
        id_to_raw_node: dict[int, CollectionNodeRaw[T]] = {}

        for raw_node in raw_nodes:
            if raw_node.id in id_to_raw_node:
                raise RuntimeError("Id appeared twice")
            
            id_to_raw_node[raw_node.id] = raw_node

        node_to_children: dict[int | None, list[int]] = {}

        for raw_node in id_to_raw_node.values():
            if raw_node.root_id == raw_node.id:
                raise RuntimeError("Node is root of itself")
            
            if raw_node.root_id is not None and raw_node.root_id not in id_to_raw_node:
                raise RuntimeError(f"Root id {raw_node.root_id} is invalid")
            
            node_to_children.setdefault(raw_node.root_id, []).append(raw_node.id)
        
        normed_value_to_node: dict[T, CollectionNode[T]] = {}

        def recursively_create_collection_nodes(root: CollectionNode[T] | None, seen: set[int]) -> CollectionNodesT[T]:
            if root is not None:
                if root.id in seen:
                    raise RuntimeError(f"Id {root.id} already seen, cyclic")
                
                seen.add(root.id)

            result: list[CollectionNode[T]] = []

            for child_id in node_to_children.get(None if root is None else root.id, []):
                child_node_raw = id_to_raw_node[child_id]

                child_node = CollectionNode(
                    id=child_node_raw.id,
                    value=child_node_raw.value,
                    aliases=child_node_raw.aliases,
                    sort_value=child_node_raw.sort_value,
                    children=(),
                    root=root
                )
                child_node._post_set_children(recursively_create_collection_nodes(child_node, seen))
                result.append(child_node)

                normed_value = attribute.value_type.norm(child_node.value)

                if normed_value in normed_value_to_node:
                    raise RuntimeError("Value appeared more than once")
                
                normed_value_to_node[normed_value] = child_node

            if root is not None:
                seen.remove(root.id)

            return tuple(result)
        
        nodes = recursively_create_collection_nodes(None, set())

        return Collection(
            attribute=attribute,
            nodes=nodes,
            normed_node_value_to_node=MappingProxyType(normed_value_to_node)
        )
            
    
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
