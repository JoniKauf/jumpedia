import enum
import typing as t
from string.templatelib import Template

from domain.entities.attribute import AttributeEntity
from domain.entities.base import BaseEntity
from domain.entities.community import CommunityEntity
from domain.entities.community_user import CommunityUserEntity, UserEntity
from domain.entities.list import ListEntity
from domain.enums.attribute import AttributeType
from domain.enums.rank import CommunityRank, MetaRank, ServerRank
from domain.errors import AnyRankT, StrStore
from interfaces.message.layout import T, _TaggedObj
from services.dtos.community import (
    CommunityInfo,
    CommunitySummary,
    DeletedCommunity,
)
from services.dtos.list import ListInfo


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


type MentionableEntityT = CommunityEntity | UserEntity | CommunityUserEntity | ListEntity | AttributeEntity

type MentionableInfoDTOT = CommunityInfo | ListInfo
type MentionableSummaryDTOT = CommunitySummary
type MentionableDeletedDTOT = DeletedCommunity
type MentionableDTOT = MentionableInfoDTOT | MentionableSummaryDTOT | MentionableDeletedDTOT

type MentionableT = AnyRankT | MentionableEntityT | MentionableDTOT

_TYPE_MAP: dict[type[MentionableT], tuple[str, str]] = {
    MetaRank: ("meta rank", "meta ranks"),
    CommunityRank: ("community rank", "community ranks"),
    ServerRank: ("server rank", "server ranks"),
    UserEntity: ("user", "users"),
    CommunityUserEntity: ("community member", "community members"),
    CommunityEntity: ("community", "communities"),
    CommunityInfo: ("community", "communities"),
    DeletedCommunity: ("community", "communities"),
    ListEntity: ("list", "lists"),
    ListInfo: ("list", "lists"),
    AttributeEntity: ("attribute", "attributes"),
}

_ATTRIBUTE_TYPE_PREFIX_MAP = {
    AttributeType.STATIC: "static",
    AttributeType.TASK: "task",
    AttributeType.USER: "user",
}


def _get_type_name_lower(mentionable_type: type[MentionableT], singular: bool) -> str:
    type_str = _TYPE_MAP[mentionable_type]

    if isinstance(mentionable_type, AttributeEntity):
        type_str = f"{_ATTRIBUTE_TYPE_PREFIX_MAP[mentionable_type.type]} {type_str}"

    return type_str[not singular]


def _get_instance_name_lower(
    mentionable: MentionableT,
) -> str:
    if isinstance(mentionable, (MetaRank, CommunityRank, ServerRank)):
        return mentionable.name.lower()

    return mentionable.name.real.value


def type_name_title(
    mentionable_type: type[MentionableT], singular: bool = True
) -> _TaggedObj:
    return _get_type_name_lower(mentionable_type, singular).title() @ T.RAW


def mention(mentionable: MentionableT, singular: bool = True) -> _TaggedObj:
    return (
        f"{_get_type_name_lower(type(mentionable), singular)} "
        f"``{_get_instance_name_lower(mentionable)}``"
    ) @ T.DEFAULT
