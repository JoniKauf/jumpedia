

from dataclasses import dataclass, field
from typing import ClassVar
from database import queries
from database.typed import Tables as TBL
from database import typed
from structures import attributes
from structures.attributes import AttributeDataCache, AttributeValueTypeT
from structures.attributes.base_attribute import BaseAttribute
from structures.attributes.collection import Collection


@dataclass(frozen=True, kw_only=True)
class UserAttribute[T: AttributeValueTypeT](BaseAttribute[T]):
    STRUCTURE_NAME: ClassVar[str] = "user attribute"
    ATTRIBUTE_TYPE_NAME: ClassVar[str] = "user"
    TYPE_ID: ClassVar[int] = 2

    _cache: AttributeDataCache[T, 'UserAttribute[T]'] = field(init=False, default_factory=AttributeDataCache)
    
    def get_aliases(self) -> frozenset[str]:
        if self._cache.aliases is not None:
            return self._cache.aliases
        
        h = queries.ArgHelper()
        Tbl = TBL.UserAttributeAlias

        with queries.connected() as (conn, cursor):
            cursor.execute(f"""
                SELECT {Tbl.alias}
                FROM {Tbl}
                WHERE {Tbl.user_attribute_id} = {h|self.id}
            """)

            rows: typed.ManyTableRowT = cursor.fetchall()

        self._cache.aliases = frozenset(row[Tbl.alias] for row in rows)
        
        return self._cache.aliases
    
    def get_collection(self) -> Collection[T, 'UserAttribute']:
        if self._cache.collection is not None:
            return self._cache.collection
        
        h = queries.ArgHelper()
        NodeTbl = TBL.UserAttributeCollectionNode
        NodeAliasTbl = TBL.UserAttributeCollectionNodeAlias

        with queries.connected() as (conn, cursor):
            
            cursor.execute(f"""
                SELECT 
                    n.*,
                    COALESCE(
                        JSON_ARRAYAGG(a.{NodeAliasTbl.alias}),
                        JSON_ARRAY()
                    ) AS {NodeTbl._aliases}
                FROM {NodeTbl} n
                LEFT JOIN {NodeAliasTbl} a
                    ON a.{NodeAliasTbl.user_attribute_collection_node_id} = n.{NodeTbl.id}
                WHERE {NodeTbl.user_attribute_id} = {h|self.id}
                GROUP BY n.{NodeTbl.id}
            """, h.steal())

        self._cache.collection = Collection.from_rows(cursor.fetchall(), self.__class__)
            
        return self._cache.collection
