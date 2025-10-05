import typing as t

from ..database import queries
from ..database import typed as typed
from ..utils import text
from . import BaseStructure

if t.TYPE_CHECKING:
    from .list import List

class Task(BaseStructure):
    list: List
    id: int
    real_name: text.RealStr
    norm_name: text.NormStr

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

    @property
    def identity(self) -> tuple[int, ...]:
        return (self.id,) + self.list.identity
        
    


# def get_contributor_line(self) -> str:
#     def join_grammatically(elems: Sequence[str]):
#         if len(elems) < 2:
#             return ''.join(elems)
#         return ', '.join((*elems[:-1], f" & {elems[-1]}"))
    
#     contributors: Generator[attrs.AttrPerson | attrs.AttrMultiValue[attrs.AttrPerson]] = (
#         v for v in self.values(lambda _, val: issubclass(val.value_cls, attrs.AttrPerson))
#     )  # type: ignore

#     action_to_people: dict[str, tuple[person.Person, ...]] = {
#         person.value_cls.ACTION: person.unpacked for person in contributors
#     }

#     people_to_action: dict[tuple[str, ...], list[str]] = {}

#     for title, value in action_to_people.items():
#         people_to_action.setdefault(
#             tuple(person.name for person in value), []
#         ).append(title)

#     # Remove empty values
#     people_to_action.pop((), None)

#     return ', '.join(
#         f"{join_grammatically(titles)} by {join_grammatically(value)}"
#         for value, titles in people_to_action.items()
#     )