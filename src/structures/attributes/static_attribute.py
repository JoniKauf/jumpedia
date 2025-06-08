from dataclasses import dataclass, field
from typing import Any, ClassVar

from database import queries
from database import typed
from database.typed import Tables as TBL

from structures.attributes import AttributeValueTypeT
from structures.attributes.abstract_attribute import AbstractAttribute
from structures.attributes.collection import Collection

@dataclass(kw_only=True)
class StaticAttribute[T: AttributeValueTypeT](AbstractAttribute[T]):
    STRUCTURE_NAME: ClassVar[str] = "static attribute"
    ATTRIBUTE_TYPE_NAME: ClassVar[str] = "static"
    TYPE_ID: ClassVar[int] = 0
    

    unique_value_per_list: bool
    
    _aliases: set[str] | None = field(init=False, default=None)
    
    def get_aliases(self) -> set[str]:
        if self._aliases is None:
            h = queries.ArgHelper()
            SAAT = TBL.StaticAttributeAlias

            with queries.connected() as (conn, cursor):
                cursor.execute(f"""
                    SELECT {TBL.StaticAttributeAlias.alias}
                    FROM {TBL.StaticAttributeAlias}
                    WHERE {TBL.StaticAttributeAlias.static_attribute_id} = {h|self.id}
                """)

                rows: typed.ManyTableRowT = cursor.fetchall()

            self._aliases = {row[SAAT.alias] for row in rows}
        
        return self._aliases
    
    def get_collection(self) -> Collection[T, Any]:
        return Collection.empty()