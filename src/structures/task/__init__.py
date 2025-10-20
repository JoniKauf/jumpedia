import typing as t
from dataclasses import field

from src.database import queries
from src.database import typed as typed
from src.structures import BaseStructure
from src.utils import text
from structures.attribute.slot_type import SlotStr

if t.TYPE_CHECKING:
    from src.structures.list import List

class Task(BaseStructure):
    list: List
    id: int
    slot_name: SlotStr
    norm_name: text.NormStr

    @property
    def identity(self) -> tuple[int, ...]:
        return (self.id,) + self.list.identity
    
    @property
    def name(self) -> str:
        return self.slot_name
    
    def get_real_aliases(self) -> frozenset[text.RealStr]:
        with queries.connected() as c:
            c.execute(lambda arg: t"""
                SELECT {typed.TaskAlias.slot_alias}
                FROM {typed.TaskAlias}
                WHERE 
                    {typed.TaskAlias.list_id} = {arg(self.list.id)}
                    AND {typed.TaskAlias.task_id} = {arg(self.id)}
            """)

            rows = c.fetchall(typed.TaskAlias)

        return frozenset(row.slot_alias for row in rows)
    
    def get_norm_aliases(self) -> frozenset[text.NormStr]:
        with queries.connected() as c:
            c.execute(lambda arg: t"""
                SELECT {typed.TaskAlias.norm_alias}
                FROM {typed.TaskAlias}
                WHERE 
                    {typed.TaskAlias.list_id} = {arg(self.list.id)}
                    AND {typed.TaskAlias.task_id} = {arg(self.id)}
            """)

            rows = c.fetchall(typed.TaskAlias)

        return frozenset(row.norm_alias for row in rows)