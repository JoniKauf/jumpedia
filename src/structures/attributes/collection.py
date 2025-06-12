

from dataclasses import dataclass
import json
import pickle
from typing import Any, Self, overload
from structures.attributes import AttributeValueTypeT
from database import typed
from database.typed import Tables as TBL
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
        return text.norm(value)
    
    return value


_MISSING = object()

@dataclass(frozen=True, unsafe_hash=True, eq=True)
class Collection[T1: AttributeValueTypeT, T2: TaskAttribute | UserAttribute]:
    nodes: CollectionNodesT[T1]
    lookup: dict[T1, CollectionNode[T1]]

    @classmethod
    def empty(cls) -> Self:
        return cls([], {})
    
    @classmethod
    def from_rows(cls, rows: typed.ManyTableRowT, attribute_type: type[T2]) -> Self:
        if not rows:
            cls([], {})
        
        lookup_by_id: dict[int, CollectionNode[T1]] = {}
        lookup_by_syn: dict[T1, CollectionNode[T1]] = {}

        result: CollectionNodesT[T1] = []

        Tbl = dbutils.get_attribute_collection_node_table(attribute_type)

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
            result, 
            lookup_by_syn
        )
    
    @property
    def is_empty(self) -> bool:
        return self.__class__.empty() == self
    
    @overload
    def lookup_node(self, value: T1) -> CollectionNode[T1]: 
        ...
    
    @overload
    def lookup_node[TDefault: Any](self, value: T1, default: TDefault) -> CollectionNode[T1] | TDefault: 
        ...

    def lookup_node(self, value: T1, default: Any = _MISSING) -> Any:
        value = normalize_collection_value(value)

        if default is _MISSING:
            return self.lookup[value]
        
        return self.lookup.get(value, default)