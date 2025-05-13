import builtins
from dataclasses import dataclass
from typing import Any, ClassVar, Final, Never, NotRequired, Self, TypedDict
from database import queries
from structures import attribute
from structures.attribute import AttributeValueTypeT
from structures.list import List
from structures.user import User
from utils import text


type AnyTask = Task | UserTask


@dataclass(frozen=True, kw_only=True)
class AbstractTask:
    MAX_SYN_LEN: ClassVar[Final[int]] = 80
    
    list: List
    id: int

    @property
    def identity(self) -> tuple[int, ...]:
        return (self.id,) + self.list.identity
    
    def __post_init__(self) -> None:
        if self.__class__ == AbstractTask:
            raise NotImplementedError()
    
    def __hash__(self) -> int:
        return hash(self.identity)
    
    def __eq__(self, value: object) -> bool:
        return isinstance(value, self.__class__) and self.identity == value.identity

    @classmethod
    def create(cls, *args: Any, **kwargs: Any) -> Never:
        raise NotImplementedError()
    

class TaskResultT(TypedDict):
    id: int

@dataclass(frozen=True, kw_only=True)
class Task(AbstractTask):
    @classmethod
    def create(cls, list: List, name: str) -> 'Task':
        h = queries.ArgHelper()
        name = text.validate_and_sanitize_name(name)

        with list.edit_lock:
            list.get_task_by_name()
            with queries.connected(list.community) as (conn, cursor):
                cursor.execute(f"""
                    INSERT INTO task (
                        list_id
                    )
                    VALUES (
                        {h|list.id}
                    )
                """)

        





@dataclass(frozen=True, kw_only=True)
class UserTask(AbstractTask):
    pass


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