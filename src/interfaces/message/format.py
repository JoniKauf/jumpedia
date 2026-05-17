from string.templatelib import Template
import typing as t

from domain.entities.base import BaseEntity
from domain.entities.community import CommunityEntity
from domain.enums.rank import CommunityRank, MetaRank, ServerRank
from domain.errors import AnyRankT, StrStore
from interfaces.protocols.named_entity import MentionableEntity
import re

def shorten(s: str, max_len: int, more: str = "...") -> str:
    if len(s) <= max_len:
        return s

    if max_len <= len(more):
        return more

    return s[: max_len - len(more)] + "..."


def human_join(
    objects: t.Sequence[t.Any], final_delimiter: str, delimiter: str = ", "
) -> str:
    objects_str = tuple(map(str, objects))

    if len(objects) <= 1:
        return delimiter.join(objects_str)

    return f"{delimiter.join(objects_str[:-1])}{final_delimiter}{objects[-1]}"


_PATTERN = re.compile(r'(?!^)([A-Z]+)')

def get_mentionable_entity_type_name(entity: MentionableEntity) -> str:
    return re.sub(_PATTERN, r' \1', type(entity).__name__.removesuffix("Entity"))


type MentionableT = AnyRankT | MentionableEntity

def mention(obj: MentionableT) -> Template:
    match obj:
        case MetaRank() | ServerRank() | CommunityRank():
            return Template(
                f"{str(type(obj)).replace("Rank", " Rank")} ``{obj.name.replace('_', ' ').title()}``"
            )

        case _:
            return Template(
                f"{get_mentionable_entity_type_name(obj)} ``{shorten(obj.name.real.value, 32)}``"
            )
