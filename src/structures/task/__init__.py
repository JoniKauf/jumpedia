from dataclasses import field
import typing as t

from src.database import queries
from src.database import typed as typed
from src.utils import text
from src.structures import BaseStructure

if t.TYPE_CHECKING:
    from src.structures.list import List

class Task(BaseStructure):
    list: List
    id: int
    real_name: text.RealStr
    norm_name: text.NormStr

    @property
    def identity(self) -> tuple[int, ...]:
        return (self.id,) + self.list.identity
    
    @property
    def name(self) -> str:
        return self.real_name
    
    def get_real_aliases(self) -> frozenset[text.RealStr]:
        with queries.connected() as c:
            c.execute(lambda arg: t"""
                SELECT {typed.TaskAlias.real_alias}
                FROM {typed.TaskAlias}
                WHERE 
                    {typed.TaskAlias.list_id} = {arg(self.list.id)}
                    AND {typed.TaskAlias.task_id} = {arg(self.id)}
            """)

            rows = c.fetchall(typed.TaskAlias)

        return frozenset(row.real_alias for row in rows)
    
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