
from dataclasses import dataclass, field
import json
from types import MappingProxyType
from typing import ClassVar, Self

from database import queries
from database.typed import Tables as TBL
from database import typed
from errors.feedback import feedbacks
from structures import attributes
from structures.attributes import AttributeDataCache, AttributeValueTypeT, RawCollectionNode, RawCollectionNodesT, UniquenessExtended
from structures.attributes.base_attribute import BaseAttribute
from structures.attributes.collection import Collection, CollectionNode, CollectionNodesT
from structures.attributes import collection
from utils import parsetools


@dataclass(frozen=True, kw_only=True)
class TaskAttribute[T: AttributeValueTypeT](BaseAttribute[T]):
    STRUCTURE_NAME: ClassVar[str] = "task attribute"
    ATTRIBUTE_TYPE_NAME: ClassVar[str] = "task"
    TYPE_ID: ClassVar[int] = 1

    uniqueness: UniquenessExtended

    _cache: AttributeDataCache[T] = field(init=False, default_factory=AttributeDataCache)
    
    
    def get_aliases(self) -> frozenset[str]:
        if self._cache.aliases is not None:
            return self._cache.aliases
        
        h = queries.ArgHelper()
        Tbl = TBL.TaskAttributeAlias

        with queries.connected() as (conn, cursor):
            cursor.execute(f"""
                SELECT {Tbl.alias}
                FROM {Tbl}
                WHERE {Tbl.task_attribute_id} = {h|self.id}
            """)

            rows: typed.ManyTableRowT = cursor.fetchall()
        
        self._cache.aliases = frozenset(row[Tbl.alias] for row in rows)

        return self._cache.aliases
    

    def _create_collection(self, raw_nodes: RawCollectionNodesT[T]) -> 'Collection[T]':
        if not raw_nodes:
            return Collection(
                attribute=self,
                top_nodes=frozenset(),
                normed_node_value_to_node=MappingProxyType({})
            )
        
        normed_to_node: dict[T, CollectionNode[T]] = {}

        def recursively_create_children(parent: None | CollectionNode[T], raw_node: RawCollectionNode[T]) -> CollectionNode[T]:
            node = CollectionNode(
                value=raw_node.value,
                aliases=frozenset(raw_node.aliases),
                sort_value=raw_node.sort_value,
                children=frozenset(),
                parent=parent,
                value_type=self.value_type
            )

            node._post_set_children(frozenset(
                recursively_create_children(node, child) 
                for child in 
                raw_node.children
            ))

            for syn in (node.value, *node.aliases):
                normed = self.value_type.norm(syn)

                if normed in normed_to_node:
                    raise feedbacks.temp("Same syn appeared twice")
                
                normed_to_node[normed] = node
            
            return node
        
        top_nodes = frozenset(recursively_create_children(None, raw_node) for raw_node in raw_nodes)

        TblNodes = TBL.TaskAttributeCollectionNode
        TblAliases = TBL.TaskAttributeCollectionNodeAlias
        
        def recursively_insert_children(parent_id: int | None, nodes: CollectionNodesT[T]) -> None:
            if not nodes:
                return
            
            
            for node in nodes:
                cursor.execute(f"""
                    INSERT INTO {TblNodes} (
                        {TblNodes.task_attribute_id},
                        {TblNodes.value},
                        {TblNodes.sort_value},
                        {TblNodes.parent_id}
                    ) 
                    VALUES (
                        {h|self.id},
                        {h|node.value},
                        {h|node.sort_value},
                        {h|parent_id}
                    )
                """)

                node_id: int = cursor.lastrowid  # type: ignore

                cursor.execute(f"""
                    INSERT INTO {TblAliases} (
                        {TblAliases.task_attribute_collection_node_id},
                        {TblAliases.alias}
                    )
                    VALUES 
                        {','.join(f"""""" for alias in node.aliases)}
                """)

        h = queries.ArgHelper()
        with queries.connected() as (_, cursor), self.locked:
            




    def get_collection(self) -> Collection[T]:
        if self._cache.collection is not None:
            return self._cache.collection
        
        h = queries.ArgHelper()
        TblNode = TBL.TaskAttributeCollectionNode
        TblNodeAlias = TBL.TaskAttributeCollectionNodeAlias

        with queries.connected() as (conn, cursor):
            cursor.execute(f"""
                SELECT 
                    n.*,
                    COALESCE(
                        JSON_ARRAYAGG(a.{TblNodeAlias.alias}),
                        JSON_ARRAY()
                    ) AS {TblNode._aliases}
                FROM {TblNode} n
                LEFT JOIN {TblNodeAlias} a
                    ON a.{TblNodeAlias.task_attribute_collection_node_id} = n.{TblNode.id}
                WHERE {TblNode.task_attribute_id} = {h|self.id}
                GROUP BY n.{TblNode.id}
            """, h.steal())

            result: typed.ManyTableRowT = cursor.fetchall()
        
        self._cache.collection = Collection.create([
            collection.CollectionNodeRaw(
                id=row[TblNode.id],
                value=row[TblNode.value],
                aliases=json.loads(row[TblNode._aliases]),
                sort_value=row[TblNode.sort_value],
                root_id=row[TblNode.parent_id]
            )
            for row in result
        ], self)

        return self._cache.collection