from dataclasses import dataclass, field
from typing import Any, ClassVar

from database import queries
from database import typed
from database.typed import Tables as TBL

from structures import attributes
from structures.attributes import AttributeValueTypeT
from structures.attributes.abstract_attribute import BaseAttribute
from structures.attributes.collection import Collection

@dataclass(frozen=True, kw_only=True)
class StaticAttribute[T: AttributeValueTypeT](BaseAttribute[T]):
    __structure_name__ = "static attribute"

    TYPE_ID: ClassVar[int] = 0
    
    unique_value_per_list: bool
    
    _aliases: frozenset[str] | None = field(init=False, default=None)

    def get_aliases(self) -> frozenset[str]:
        if self._aliases is None:
            h = queries.ArgHelper()
            Tbl = TBL.StaticAttributeAlias

            with queries.connected() as (conn, cursor):
                cursor.execute(f"""
                    SELECT {Tbl.alias}
                    FROM {Tbl}
                    WHERE {Tbl.static_attribute_id} = {h|self.id}
                """)

                rows: typed.ManyTableRowT = cursor.fetchall()

            attributes._post_set_aliases(self, frozenset(row[Tbl.alias] for row in rows))
            assert self._aliases is not None
        
        return self._aliases
    
    def get_collection(self) -> Collection[T, Any]:
        return Collection.empty()