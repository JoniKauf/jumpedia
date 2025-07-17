

from abc import abstractmethod
from dataclasses import dataclass, field
import pickle
from types import MappingProxyType
from typing import Any, ClassVar, Final, Iterable, Protocol, Self, Sequence, overload
from database.static import BaseRow, Rows
from errors.feedback import feedbacks
from structures.attributes import AnyAttributeT, AttributeTables, BaseAttribute, RawCollectionNode, RawCollectionNodesT
from database import layout, queries
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
    # We support StaticAttribute for empty(), but other methods only work without StaticAttribute
    attribute: BaseAttribute[T, Any, Any, Any]
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
    

@dataclass(frozen=True)
class AttributeTablesWithCollection[
    T1: layout.BaseAttribute, 
    T2: layout.BaseAttributeAlias, 
    T3: layout.BaseAttributeTaskValue, 
    T4: layout.BaseAttributeCollectionNode, 
    T5: layout.BaseAttributeCollectionNodeAlias
](AttributeTables[T1, T2, T3]):
    attribute_collection_node: type[T4]
    attribute_collection_node_alias: type[T5]


class BaseCollectionAttribute[
    T: SlotTypeT,
    T1: layout.BaseAttribute, 
    T2: layout.BaseAttributeAlias, 
    T3: layout.BaseAttributeTaskValue, 
    T4: layout.BaseAttributeCollectionNode, 
    T5: layout.BaseAttributeCollectionNodeAlias
](BaseAttribute[T, T1, T2, T3]):
    @staticmethod
    @abstractmethod
    def tables() -> AttributeTablesWithCollection[T1, T2, T3, T4, T5]:
        pass

    def __post_init__(self) -> None:
        if self.__class__ == BaseCollectionAttribute:
            raise RuntimeError
        
        return super().__post_init__()
    
    def get_collection(self) -> Collection[T]:
        h = queries.ArgHelper()

        TblNode = self.__class__.tables().attribute_collection_node
        TblNodeAlias = self.__class__.tables().attribute_collection_node_alias

        with queries.connected() as (conn, cursor):
            cursor.execute(f"""
                SELECT *
                FROM {TblNode}
                WHERE {TblNode.attribute_id} = {h|self.id}
            """, h.steal())

            result = Rows(cursor.fetchall(), TblNode)

            cursor.execute(f"""
                SELECT 
                    {TblNodeAlias.attribute_collection_node_id},
                    {TblNodeAlias.alias}
                FROM
                    {TblNodeAlias}
                WHERE
                    {TblNodeAlias.attribute_id} = {h|self.id}
            """, h.steal())

            aliases_result = Rows(cursor.fetchall(), layout.Snippets.SnippetBaseAttributeCollectionNode)

        del TblNodeAlias

        row_id_to_row = {row.id: row for row in result}
        row_id_to_child_row_ids: dict[int, list[int]] = {}

        top_rows: list[T4] = []
        row_id_to_aliases: dict[int, list[str]] = {}

        for row in result:
            row_id_to_child_row_ids \
                .setdefault(row.parent_id, []) \
                .append(row.id)
            
            if row.parent_id is None:
                top_rows.append(row)
        
            row_id_to_aliases[row.id] = []

        for alias_row in aliases_result:
            row = row_id_to_row[alias_row.attribute_collection_node_id]
            row_id_to_aliases[row.id].append(pickle.loads(alias_row.alias))

        normed_syn_to_node: dict[T, CollectionNode[T]] = {}

        def recursively_create_children(parent: CollectionNode[T] | None, row: T4) -> CollectionNode[T]:
            node = CollectionNode(
                value=pickle.loads(row.value),
                aliases=frozenset(row_id_to_aliases[row.id]),
                sort_value=row.sort_value,
                children=frozenset(),
                parent=parent,
                slot_type=self.slot_type
            )

            children_ids = row_id_to_child_row_ids.get(row.id, [])

            if children_ids:
                node._post_set_children(frozenset(
                    recursively_create_children(node, row_id_to_row[child_id])
                    for child_id in children_ids
                ))

            for syn in (node.value, *node.aliases):
                normed_syn_to_node[self.slot_type.norm(syn)] = node

            return node

        top_nodes = frozenset(recursively_create_children(None, row) for row in top_rows)
            
        return Collection(
            attribute=self,
            top_nodes=top_nodes,
            normed_syn_to_node=MappingProxyType(normed_syn_to_node)
        )


    def set_collection_helper(
        self,
        top_raw_nodes: RawCollectionNodesT[T], 
    ) -> 'Collection[T]':
        if not top_raw_nodes:
            return Collection(
                attribute=self,
                top_nodes=frozenset(),
                normed_syn_to_node=MappingProxyType({})
            )
        
        normed_to_node: dict[T, CollectionNode[T]] = {}
        node_count: int = 0

        def recursively_create_children(parent: None | CollectionNode[T], raw_node: RawCollectionNode[T], depth: int) -> CollectionNode[T]:
            if depth > MAX_DEPTH:
                raise feedbacks.temp("Max collection depth exceeded")

            nonlocal node_count
            node_count += 1

            if node_count > MAX_ELEMS:
                raise feedbacks.temp("Max amount of collection elems surpassed!")
            
            if not numbers.is_int32(raw_node.sort_value):
                raise feedbacks.temp("Sort value out of range")
            
            normed_value: T = self.slot_type.norm(raw_node.value)
            aliases: set[T] = set(map(self.slot_type.norm, raw_node.aliases))

            if normed_value in aliases:
                aliases.remove(normed_value)
            
            node = CollectionNode(
                value=raw_node.value,
                aliases=frozenset(aliases),
                sort_value=raw_node.sort_value,
                children=frozenset(),
                parent=parent,
                slot_type=self.slot_type
            )

            depth += 1
            
            node._post_set_children(frozenset(
                recursively_create_children(node, child, depth) 
                for child in 
                raw_node.children
            ))

            for normed_syn in (normed_value, *node.aliases):
                if normed_syn in normed_to_node:
                    raise feedbacks.temp("Same syn appeared twice")
                
                normed_to_node[normed_syn] = node
            
            return node
        
        top_nodes = frozenset(recursively_create_children(None, raw_node, 1) for raw_node in top_raw_nodes)

        TblNodes = self.__class__.tables().attribute_collection_node
        TblAliases = self.__class__.tables().attribute_collection_node_alias
        
        def recursively_insert_children(parent_id: int | None, nodes: CollectionNodesT[T]) -> None:
            if not nodes:
                return
            
            for node in nodes:
                cursor.execute(f"""
                    INSERT INTO {TblNodes} (
                        {TblNodes.attribute_id},
                        {TblNodes.value},
                        {TblNodes.sort_value},
                        {TblNodes.parent_id}
                    ) 
                    VALUES (
                        {h|self.id},
                        {h|pickle.dumps(node.value)},
                        {h|node.sort_value},
                        {h|parent_id}
                    )
                """, h.steal())

                node_id: int = cursor.lastrowid  # type: ignore

                if node.aliases:
                    cursor.execute(f"""
                        INSERT INTO {TblAliases} (
                            {TblAliases.attribute_id},
                            {TblAliases.attribute_collection_node_id},
                            {TblAliases.alias}
                        )
                        VALUES 
                            {','.join(f"""(
                                {h|self.id},
                                {h|node_id},
                                {h|pickle.dumps(alias)}
                            )""" for alias in node.aliases)}
                    """, h.steal())

                recursively_insert_children(node_id, node.children)

        h = queries.ArgHelper()

        with queries.connected() as (_, cursor), self.locked:
            # We go from top nodes down the tree so we can be sure
            # the parent_id is already inserted and the foreign key
            # check succeeds
            recursively_insert_children(None, top_nodes)

        return Collection(
            attribute=self,
            top_nodes=top_nodes,
            normed_syn_to_node=MappingProxyType(normed_to_node)
        )