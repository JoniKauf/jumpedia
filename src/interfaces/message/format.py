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
from services.dtos.community import DeletedCommunityDto


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
type MentionableDtoT = DeletedCommunityDto

type MentionableT = AnyRankT | MentionableEntityT | MentionableDtoT


class Mention:
    def __init__(self, mentionable: MentionableT) -> None:
        self._mentionable = mentionable
        self._type_name, self._obj_name = self._get_type_and_obj_name_lower(mentionable)

    # This is purposefully very static and not dynamic with classes' __name__ to allow for
    # more customization if needed and to not have internal renames affect user-sided representation
    @staticmethod
    def _get_type_and_obj_name_lower(mentionable: MentionableT) -> tuple[str, str]:
        match mentionable:
            case MetaRank() | CommunityRank() | ServerRank():
                type_str: str

                match mentionable:
                    case MetaRank():
                        type_str = "meta"
                    case CommunityRank():
                        type_str = "community"
                    case ServerRank():
                        type_str = "server"
                    case _:
                        t.assert_never(mentionable)

                type_str += " rank"

                return (type_str, mentionable.name.replace("_", " ").title())

            case (
                UserEntity()
                | CommunityUserEntity()
                | CommunityEntity()
                | ListEntity()
                | AttributeEntity()
                | DeletedCommunityDto()
            ):
                type_str: str

                match mentionable:
                    case UserEntity():
                        type_str = "user"
                    case CommunityUserEntity():
                        type_str = "community member"
                    case CommunityEntity() | DeletedCommunityDto():
                        type_str = "community"
                    case ListEntity():
                        type_str = "list"
                    case AttributeEntity():
                        match mentionable.type:
                            case AttributeType.STATIC:
                                type_str = "static attribute"
                            case AttributeType.TASK:
                                type_str = "task attribute"
                            case AttributeType.USER:
                                type_str = "user attribute"
                            case _:
                                t.assert_never(mentionable)
                    case _:
                        t.assert_never(mentionable)

                return (type_str, mentionable.name.real.value)

            case _:
                t.assert_never(mentionable)

    @property
    def type_title(self) -> _TaggedObj:
        return self._type_name.title() @ T.RAW

    @property
    def mention(self) -> _TaggedObj:
        return f"{self._type_name} ``{self._obj_name}``" @ T.DEFAULT
