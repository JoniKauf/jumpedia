

from dataclasses import dataclass, field
from typing import ClassVar
from database import queries
from database.typed import Tables as TBL
from database import typed
from structures import attributes
from structures.attributes import AttributeValueTypeT
from structures.attributes.abstract_attribute import BaseAttribute
from structures.attributes.collection import Collection


@dataclass(frozen=True, kw_only=True)
class UserAttribute[T: AttributeValueTypeT](BaseAttribute[T]):
    STRUCTURE_NAME: ClassVar[str] = "user attribute"
    ATTRIBUTE_TYPE_NAME: ClassVar[str] = "user"
    TYPE_ID: ClassVar[int] = 2

    _aliases: frozenset[str] | None = field(init=False, default=None)
    _collection: Collection[T, 'UserAttribute'] | None = field(init=False, default=None)

    def get_aliases(self) -> frozenset[str]:
        if self._aliases is None:
            h = queries.ArgHelper()
            Tbl = TBL.UserAttributeAlias

            with queries.connected() as (conn, cursor):
                cursor.execute(f"""
                    SELECT {Tbl.alias}
                    FROM {Tbl}
                    WHERE {Tbl.user_attribute_id} = {h|self.id}
                """)

                rows: typed.ManyTableRowT = cursor.fetchall()

            attributes._post_set_aliases(self, frozenset(row[Tbl.alias] for row in rows))
            assert self._aliases is not None
        
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

            attributes._post_set_collection(self, Collection.from_rows(cursor.fetchall(), self.__class__))
            assert self._collection is not None
            
        return self._collection
