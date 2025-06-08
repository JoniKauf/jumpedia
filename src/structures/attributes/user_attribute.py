

from dataclasses import dataclass, field
from typing import ClassVar
from database import queries
from database.typed import Tables as TBL
from database import typed
from structures.attributes import AttributeValueTypeT
from structures.attributes.abstract_attribute import AbstractAttribute
from structures.attributes.collection import Collection


@dataclass(kw_only=True)
class UserAttribute[T: AttributeValueTypeT](AbstractAttribute[T]):
    STRUCTURE_NAME: ClassVar[str] = "user attribute"
    ATTRIBUTE_TYPE_NAME: ClassVar[str] = "user"
    TYPE_ID: ClassVar[int] = 2

    _aliases: set[str] | None = field(init=False, default=None)
    _collection: Collection[T, 'UserAttribute'] | None = field(init=False, default=None)

    def get_aliases(self) -> set[str]:
        if self._aliases is None:
            h = queries.ArgHelper()
            SAAT = TBL.UserAttributeAlias

            with queries.connected() as (conn, cursor):
                cursor.execute(f"""
                    SELECT {SAAT.alias}
                    FROM {SAAT}
                    WHERE {SAAT.user_attribute_id} = {h|self.id}
                """)

                rows: typed.ManyTableRowT = cursor.fetchall()

            self._aliases = {row[SAAT.alias] for row in rows}
        
        return self._aliases
    
    def get_collection(self) -> Collection[T, 'UserAttribute']:
        if self._collection is None:
            h = queries.ArgHelper()
            UACNT = TBL.UserAttributeCollectionNode
            UACNAT = TBL.UserAttributeCollectionNodeAlias

            with queries.connected() as (conn, cursor):
                
                cursor.execute(f"""
                    SELECT 
                        n.*,
                        COALESCE(
                            JSON_ARRAYAGG(a.{UACNAT.alias}),
                            JSON_ARRAY()
                        ) AS {UACNT._aliases}
                    FROM {UACNT} n
                    LEFT JOIN {UACNAT} a
                        ON a.{UACNAT.user_attribute_collection_node_id} = n.{UACNT.id}
                    WHERE {UACNT.user_attribute_id} = {h|self.id}
                    GROUP BY n.{UACNT.id}
                """, h.steal())

            self._collection = Collection.from_rows(cursor.fetchall(), self.__class__)

        return self._collection
