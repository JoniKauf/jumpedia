from string.templatelib import Template
import typing as t

from domain.entities.base import BaseEntity
from domain.entities.community import CommunityEntity
from domain.enums.rank import CommunityRank, MetaRank, ServerRank
from domain.errors import AnyRankT, StrStore
import re

from services.dtos.community import DeletedCommunityDTO

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


type Mentionable = AnyRankT | MentionableEntity | DeletedCommunityDTO



def mentionable_to_type_and_obj_name(mentionable: Mentionable) -> tuple[str, str]:
    match mentionable:
        case MetaRank() | CommunityRank() | ServerRank():
            return (type(mentionable).__name__.replace("Rank", " Rank"), mentionable.name.replace('_', ' ').title())
        
        case MentionableEntity():
            return (type(mentionable).__name__.replace("Entity", ""), mentionable.name.)
def mention(obj: Mentionable) -> Template:
    type_s, obj_s = mentionable_to_type_and_obj_name(obj)
    return Template(f"{type_s} ``{obj_s}``")
