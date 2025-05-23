import builtins
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar, Iterable, Never, NotRequired, Self, TypedDict
from database import queries
from utils import text
from database import strong as S
from database.strong import Tables as TBL

from structures import user as user_

from structures.tavc import Tavc, Tuavc

if TYPE_CHECKING:
    from structures.list import List
    from structures.user import UserIdentifierT

@dataclass(frozen=True, kw_only=True)
class Task:
    MAX_SYN_LEN: ClassVar[int] = 80
    STATIC_NAME_ATTRIBUTE_NAME: ClassVar[str] = 'Name'
    STATIC_ALIAS_ATTRIBUTE_NAME: ClassVar[str] = 'Alias'

    list: 'List'
    id: int
    name: str

    @property
    def aliases(self) -> frozenset[str]:
        h = queries.ArgHelper()

        with queries.connected() as (conn, cursor):
            cursor.execute(f"""
                SELECT {TBL.TaskAlias.alias}
                FROM {TBL.TaskAlias}
                WHERE 
                    {TBL.TaskAlias.list_id} = {h|self.list.id}
                    AND {TBL.TaskAlias.task_id} = {h|self.id}
            """)

            result: S.ManyTableRowT = cursor.fetchall()

        return frozenset(row[TBL.TaskAlias.alias] for row in result)

    @property
    def identity(self) -> tuple[int, ...]:
        return (self.id,) + self.list.identity
    
    def __hash__(self) -> int:
        return hash(self.identity)
    
    def __eq__(self, value: object) -> bool:
        return isinstance(value, self.__class__) and self.identity == value.identity
    
    def get_tavc(self) -> Tavc:
        return Tavc(task=self)
    
    def get_tuavc(self, user: 'UserIdentifierT') -> Tuavc:
        from structures.user import User
        return Tuavc(task=self, user_id=user_.extract_id(user))
        
    


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