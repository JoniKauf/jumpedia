
from dataclasses import dataclass, field
from typing import ClassVar

from database import queries
from database.typed import Tables as TBL
from database import typed
from structures.attributes import AttributeValueTypeT
from structures.attributes.abstract_attribute import AbstractAttribute
from structures.attributes.collection import Collection
from structures.attributes import collection


@dataclass(kw_only=True)
class TaskAttribute[T: AttributeValueTypeT](AbstractAttribute[T]):
    STRUCTURE_NAME: ClassVar[str] = "task attribute"
    ATTRIBUTE_TYPE_NAME: ClassVar[str] = "task"
    TYPE_ID: ClassVar[int] = 1

    unique_value_per_list: bool

    _aliases: set[str] | None = field(init=False, default=None)
    _collection: Collection[T, 'TaskAttribute'] | None = field(init=False, default=None)
    
    def get_aliases(self) -> set[str]:
        if self._aliases is None:
            h = queries.ArgHelper()
            SAAT = TBL.TaskAttributeAlias

            with queries.connected() as (conn, cursor):
                cursor.execute(f"""
                    SELECT {SAAT.alias}
                    FROM {SAAT}
                    WHERE {SAAT.task_attribute_id} = {h|self.id}
                """)

                rows: typed.ManyTableRowT = cursor.fetchall()

            self._aliases = {row[SAAT.alias] for row in rows}
        
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

            self._collection = Collection.from_rows(cursor.fetchall(), self.__class__)

        return self._collection