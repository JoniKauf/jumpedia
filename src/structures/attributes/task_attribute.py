
from dataclasses import dataclass, field
from typing import ClassVar

from database import queries
from database.typed import Tables as TBL
from database import typed
from structures import attributes
from structures.attributes import AttributeValueTypeT
from structures.attributes.abstract_attribute import BaseAttribute
from structures.attributes.collection import Collection
from structures.attributes import collection


@dataclass(frozen=True, kw_only=True)
class TaskAttribute[T: AttributeValueTypeT](BaseAttribute[T]):
    STRUCTURE_NAME: ClassVar[str] = "task attribute"
    ATTRIBUTE_TYPE_NAME: ClassVar[str] = "task"
    TYPE_ID: ClassVar[int] = 1

    unique_value_per_list: bool

    _aliases: frozenset[str] | None = field(init=False, default=None)
    _collection: Collection[T, 'TaskAttribute'] | None = field(init=False, default=None)
    
    def get_aliases(self) -> frozenset[str]:
        if self._aliases is None:
            h = queries.ArgHelper()
            Tbl = TBL.TaskAttributeAlias

            with queries.connected() as (conn, cursor):
                cursor.execute(f"""
                    SELECT {Tbl.alias}
                    FROM {Tbl}
                    WHERE {Tbl.task_attribute_id} = {h|self.id}
                """)

                rows: typed.ManyTableRowT = cursor.fetchall()

            attributes._post_set_aliases(self, frozenset(row[Tbl.alias] for row in rows))
            assert self._aliases is not None
        
        return self._aliases
    

    def get_collection(self) -> Collection[T, 'TaskAttribute']:
        if self._collection is None:
            h = queries.ArgHelper()
            TACNT = TBL.TaskAttributeCollectionNode
            TACNAT = TBL.TaskAttributeCollectionNodeAlias

            with queries.connected() as (conn, cursor):
                
                cursor.execute(f"""
                    SELECT 
                        n.*,
                        COALESCE(
                            JSON_ARRAYAGG(a.{TACNAT.alias}),
                            JSON_ARRAY()
                        ) AS {TACNT._aliases}
                    FROM {TACNT} n
                    LEFT JOIN {TACNAT} a
                        ON a.{TACNAT.task_attribute_collection_node_id} = n.{TACNT.id}
                    WHERE {TACNT.task_attribute_id} = {h|self.id}
                    GROUP BY n.{TACNT.id}
                """, h.steal())

            attributes._post_set_collection(self, Collection.from_rows(cursor.fetchall(), self.__class__))
            assert self._collection is not None
            
        return self._collection