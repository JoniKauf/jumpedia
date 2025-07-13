

from typing import Final
import builtins
from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from database import queries
from structures.base_structure import BaseStructure
from utils import text
from database import typed as typed
from database.typed import Tables as Tables

if TYPE_CHECKING:
    from structures.list import List

STATIC_NAME_ATTRIBUTE_NAME: Final[str] = 'name'
STATIC_ALIASES_ATTRIBUTE_NAME: Final[str] = 'aliases'

MIN_SYN_LEN: Final[int] = 1
MAX_SYN_LEN: Final[int] = 128

@dataclass(frozen=True, kw_only=True)
class Task(BaseStructure):
    __structure_name__ = 'task'

    list: 'List'
    id: int
    name: str

    @property
    def aliases(self) -> frozenset[str]:
        h = queries.ArgHelper()

        with queries.connected() as (conn, cursor):
            cursor.execute(f"""
                SELECT {Tables.TaskAlias.alias}
                FROM {Tables.TaskAlias}
                WHERE 
                    {Tables.TaskAlias.list_id} = {h|self.list.id}
                    AND {Tables.TaskAlias.task_id} = {h|self.id}
            """)

            result: typed.ManyTableRowT = cursor.fetchall()

        return frozenset(row[Tables.TaskAlias.alias] for row in result)

    @property
    def identity(self) -> tuple[int, ...]:
        return (self.id,) + self.list.identity

    @property
    def parent(self) -> List:
        return self.list

        
    


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