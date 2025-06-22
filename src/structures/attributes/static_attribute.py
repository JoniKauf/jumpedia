from dataclasses import dataclass, field
from typing import Any, ClassVar

from database import queries
from database import typed
from database.typed import Tables as TBL

from structures import attributes
from structures.attributes import AttributeDataCache, AttributeValueTypeT, UniquenessExtended
from structures.attributes.base_attribute import BaseAttribute
from structures.attributes.collection import Collection

@dataclass(frozen=True, kw_only=True)
class StaticAttribute[T: AttributeValueTypeT](BaseAttribute[T]):
    __structure_name__ = "static attribute"

    TYPE_ID: ClassVar[int] = 0
    
    uniqueness: UniquenessExtended
    
    _cache: AttributeDataCache[T] = field(init=False, default_factory=AttributeDataCache)
    
    def get_aliases(self) -> frozenset[str]:
        if self._cache.aliases is not None:
            return self._cache.aliases
        
        h = queries.ArgHelper()
        Tbl = TBL.StaticAttributeAlias

        with queries.connected() as (conn, cursor):
            cursor.execute(f"""
                SELECT {Tbl.alias}
                FROM {Tbl}
                WHERE {Tbl.static_attribute_id} = {h|self.id}
            """)

            rows: typed.ManyTableRowT = cursor.fetchall()
        
        self._cache.aliases = frozenset(row[Tbl.alias] for row in rows)

        return self._cache.aliases
    
    
    def get_collection(self) -> Collection[T]:
        return Collection.empty(self)