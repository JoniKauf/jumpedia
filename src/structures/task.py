import builtins
from dataclasses import dataclass
from typing import ClassVar, Final, NotRequired, TypedDict
from structures import attribute
from structures.attribute import Attribute, AttributeValueTypeT
from structures.list import List
from structures.user import User


class TaskResultT(TypedDict):
    task_id: int
    user_id: int
    attribute_id: int
    idx: int 
    value: str
    max_idx: int



@dataclass(frozen=True, kw_only=True)
class Task:
    list: List
    user: User
    id: int
    values: dict[Attribute, builtins.list[AttributeValueTypeT]]

    TABLE_PREFIX: ClassVar[Final[str]] = f"{__name__}_"
    USER_TABLE_PREFIX: ClassVar[Final[str]] = f"{User.__name__}_{__name__}_"

    @property
    def identity(self) -> tuple[int, ...]:
        return (self.id,) + self.list.identity
    
    def __hash__(self) -> int:
        return hash(self.identity)
    
    def __eq__(self, value: object) -> bool:
        return isinstance(value, self.__class__) and self.identity == value.identity
    
    
    

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