from enum import Enum, auto
from functools import cached_property
import functools
from typing import Any, Generator, Optional, Sequence, overload, override
from dataclasses import dataclass

from trickjump import attributes as attrs
from trickjump import attributes
from trickjump.attributes import AttributeComboClass, Finder, Taser, Prover
from discordtools import messagetools as msgt
from users import person


type TrickjumpDataT = dict[str, Any]

@dataclass(init=False, slots=True)
class Trickjump(AttributeComboClass):
    name: attrs.Name
    location: attrs.AttrMultiValue[attrs.Location]
    difficulty: attrs.Difficulty
    type: attrs.AttrMultiValue[attrs.Type]
    server: attrs.Server
    finder: attrs.AttrMultiValue[attrs.Finder]
    taser: attrs.AttrMultiValue[attrs.Taser]
    prover: attrs.AttrMultiValue[attrs.Prover]
    found_at: attrs.FoundAt
    tased_at: attrs.TasedAt
    proven_at: attrs.ProvenAt
    link: attrs.AttrMultiValue[attrs.Link]
    info: attrs.Info
    tag: attrs.AttrMultiValue[attrs.Tag]
    thumbnail: attrs.Thumbnail

    def as_info(self) -> str:
        return "\n".join(f"{elem.NAME}: {elem.value}" for elem in self.__dict__.values())

    def get_contributor_line(self) -> str:
        def join_grammatically(elems: Sequence[str]):
            if len(elems) < 2:
                return ''.join(elems)
            return ', '.join((*elems[:-1], f" & {elems[-1]}"))
        
        contributors: Generator[attrs.AttrPerson | attrs.AttrMultiValue[attrs.AttrPerson]] = (
            v for v in self.values(lambda attr: issubclass(attr.value_cls, attrs.AttrPerson))
        )  # type: ignore

        action_to_people: dict[str, tuple[person.Person, ...]] = {
            person.value_cls.ACTION: person.unpacked for person in contributors
        }

        people_to_action: dict[tuple[str, ...], list[str]] = {}

        for title, value in action_to_people.items():
            people_to_action.setdefault(
                tuple(person.value for person in value), []
            ).append(title)

        # Remove empty values
        people_to_action.pop((), None)

        return ', '.join(
            f"{join_grammatically(titles)} by {join_grammatically(value)}"
            for value, titles in people_to_action.items()
        )