import enum
from string.templatelib import Template
import typing as t

from domain.entities.attribute import AttributeEntity
from domain.entities.base import BaseEntity
from domain.entities.community import CommunityEntity
from domain.entities.list import ListEntity
from domain.entities.user import CommunityUserEntity, UserEntity
from domain.enums.attribute import AttributeType
from domain.enums.rank import CommunityRank, MetaRank, ServerRank
from domain.errors import AnyRankT, StrStore

from interfaces.message.layout import T, _TaggedObj
from services.dtos.community import CommunityInfoDTO, CommunitySummaryDTO, DeletedCommunityDTO
from services.dtos.list import ListInfoDTO


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

type MentionableInfoDTOT = CommunityInfoDTO | ListInfoDTO
type MentionableSummaryDTOT = CommunitySummaryDTO
type MentionableDeletedDTOT = DeletedCommunityDTO
type MentionableDTOT = MentionableInfoDTOT | MentionableSummaryDTOT | MentionableDeletedDTOT

type MentionableT = AnyRankT | MentionableEntityT | MentionableDTOT


class Mention:
    def __init__(self, mentionable: MentionableT) -> None:
        self._mentionable = mentionable
        self._type_name, self._obj_name = self.get_type_name_lower(mentionable)

    _TYPE_MAP: dict[type[MentionableT], str] = {
        MetaRank: "meta rank",
        CommunityRank: "community rank",
        ServerRank: "server rank",

        UserEntity: "user",
        CommunityUserEntity: "community member",
        CommunityEntity: "community",
        CommunityInfoDTO: "community",
        DeletedCommunityDTO: "community",
        ListEntity: "list",
        ListInfoDTO: "list",
        AttributeEntity: "attribute",
    }

    _ATTRIBUTE_TYPE_MAP = {
        AttributeType.STATIC: "static",
        AttributeType.TASK: "task",
        AttributeType.USER: "user",
    }

    # This is purposefully very static and not dynamic with classes' __name__ to allow for
    # more customization if needed and to not have internal renames affect user-sided representation
    @classmethod
    def get_type_name_lower(cls, mentionable: MentionableT | type[MentionableT]) -> str:
        if isinstance(mentionable, type):
            mentionable_type = mentionable
        else:
            mentionable_type = type(mentionable)

        type_str = cls._TYPE_MAP[mentionable_type]

        if isinstance(mentionable, AttributeEntity):
            type_str = f"{cls._ATTRIBUTE_TYPE_MAP[mentionable.type]} {type_str}"

        return type_str
    
    @classmethod
    def get_instance_name_lower(cls, mentionable: MentionableT) -> str:
        if isinstance(mentionable, MetaRank | CommunityRank | ServerRank):
            return mentionable.name.lower()
        
        return mentionable.name.real.value

    @property
    def type_title(self) -> _TaggedObj:
        return self._type_name.title() @ T.RAW

    @property
    def mention(self) -> _TaggedObj:
        return f"{self._type_name} ``{self._obj_name}``" @ T.DEFAULT