

from dataclasses import dataclass
import json
import pickle
from typing import Any, Self, overload
from structures.attributes import AnyAttributeT, AttributeValueTypeT, CollectionAttributeT
from database import typed
from database.typed import Tables as TBL
from structures.base_structure import BaseStructure
from utils import text
from database import dbutils

from structures.attributes.task_attribute import TaskAttribute
from structures.attributes.user_attribute import UserAttribute

type CollectionNodesT[T] = list[CollectionNode[T]]

@dataclass(frozen=True, unsafe_hash=True, eq=True)
class CollectionNode[T]:
    value: T
    aliases: set[T]
    sort_value: int
    nodes: CollectionNodesT[T]
    root: 'CollectionNode[T] | None' = None

    def _post_set_root(self, value: 'CollectionNode[T]') -> None:
        object.__setattr__(self, 'root', value)


def normalize_collection_value[T: AttributeValueTypeT](value: T) -> T:
    if isinstance(value, str):
        return text.sanitize(value)
    
    return value


_MISSING = object()

@dataclass(frozen=True)
class Collection[T: AttributeValueTypeT](BaseStructure):
    # We support StaticAttribute for empty(), but other methods only work without StaticAttribute
    attribute: AnyAttributeT[T]
    nodes: CollectionNodesT[T]
    lookup: dict[T, CollectionNode[T]]

    @classmethod
    def empty(cls, attribute: AnyAttributeT[T]) -> Self:
        return cls(attribute, [], {})
    
    @classmethod
    def from_rows(cls, rows: typed.ManyTableRowT, attribute: CollectionAttributeT) -> Self:
        if not rows:
            cls(attribute, [], {})
        
        lookup_by_id: dict[int, CollectionNode[T]] = {}
        lookup_by_syn: dict[T, CollectionNode[T]] = {}

        result: CollectionNodesT[T] = []

        Tbl = dbutils.get_attribute_collection_node_table(type(attribute))

        # Create objects without nodes / root references
        for row in rows:
            id = row[Tbl.id]
            
            item = CollectionNode(
                value=pickle.loads(row[Tbl.value]),
                aliases=set(json.loads(row[Tbl._aliases])),
                sort_value=row[Tbl.sort_value],
                nodes=[],
                root=None
            )

            lookup_by_id[id] = item
            
            # Create lookup via syn
            for syn in (item.value, *item.aliases):
                syn = normalize_collection_value(syn)

                if syn in lookup_by_syn:
                    raise AssertionError(
                        "Syns from collection, retrieved from database, result in collision?\n" +
                        f"For table {Tbl}, rows {rows}"
                    )
                
                lookup_by_syn[syn] = item

        # Create references of nodes / root
        for row in rows:
            id = row[Tbl.id]
            root_id = row[Tbl.root_id]

            if root_id is None:
                result.append(lookup_by_id[id])
                continue

            node = lookup_by_id[id]
            root = lookup_by_id[root_id]

            root.nodes.append(node)
            node._post_set_root(root)

        return cls(
            attribute,
            result, 
            lookup_by_syn
        )
    
    @overload
    def lookup_node(self, value: T) -> CollectionNode[T]: 
        ...
    
    @overload
    def lookup_node[TDefault: Any](self, value: T, default: TDefault) -> CollectionNode[T] | TDefault: 
        ...

    def lookup_node(self, value: T, default: Any = _MISSING) -> Any:
        value = normalize_collection_value(value)

        if default is _MISSING:
            return self.lookup[value]
        
        return self.lookup.get(value, default)