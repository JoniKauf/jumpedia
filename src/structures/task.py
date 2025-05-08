from dataclasses import dataclass
from structures import attribute
from structures.attribute import Attribute
from structures.list import List

@dataclass(frozen=True, kw_only=True)
class Task:
    list_: List
    id: int
    values: dict[Attribute, attribute.AttributeValueTypeT]

    def __hash__(self) -> int:
        return hash((self.id, hash(self.list_)))
    
    def __eq__(self, value: object) -> bool:
        return isinstance(value, Task) and self.id == value.id and self.list_ == value.list_
    
    def get_attributes(self):
        return self.list_.get_attributes()

    def debug_info(self) -> str:
        return "\n".join(f"{k}: {v}" for k, v in self.values.items())
    

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