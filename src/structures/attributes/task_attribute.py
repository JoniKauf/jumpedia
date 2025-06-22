
from dataclasses import dataclass, field
from typing import ClassVar, Self

from database import queries
from database.typed import Tables as TBL
from database import typed
from structures import attributes
from structures.attributes import AttributeDataCache, AttributeValueTypeT, UniquenessExtended
from structures.attributes.base_attribute import BaseAttribute
from structures.attributes.collection import Collection
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

            self._cache.collection = Collection.from_rows(cursor.fetchall(), self)

        return self._cache.collection