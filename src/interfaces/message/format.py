import typing as t

from domain.entities.attribute import AttributeEntity
from domain.entities.community import CommunityEntity
from domain.entities.list import ListEntity
from domain.entities.member import MemberEntity, UserEntity
from domain.entities.task import TaskEntity
from domain.enums.attribute import AttributeType
from domain.enums.rank import CommunityRank, MetaRank, ServerRank
from domain.errors.business import AnyRankT
from interfaces.message.layout import T, _TaggedObj
from services.dtos.attribute import (
    AttributeInfo,
    AttributeSummary,
    PreparedDeleteAttribute,
)
from services.dtos.community import (
    CommunityInfo,
    CommunitySummary,
    PreparedDeleteCommunity,
)
from services.dtos.list import DeletedList, ListInfo, ListSummary
from services.dtos.task import PreparedDeleteTask


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


type MentionableEntityT = CommunityEntity | UserEntity | MemberEntity | ListEntity | AttributeEntity | TaskEntity

type MentionableInfoDTOT = CommunityInfo | ListInfo | AttributeInfo | TaskEntity
type MentionableSummaryDTOT = CommunitySummary | ListSummary | AttributeSummary | TaskEntity
type MentionablePreparedDTOT = PreparedDeleteCommunity | DeletedList | PreparedDeleteAttribute | PreparedDeleteTask
type MentionableDTOT = MentionableInfoDTOT | MentionableSummaryDTOT | MentionablePreparedDTOT

type MentionableT = AnyRankT | MentionableEntityT | MentionableDTOT

TYPE_MAP: dict[type[MentionableT], tuple[str, str]] = {
    MetaRank: ("meta rank", "meta ranks"),
    CommunityRank: ("community rank", "community ranks"),
    ServerRank: ("server rank", "server ranks"),
    UserEntity: ("user", "users"),
    MemberEntity: ("community member", "community members"),
    CommunityEntity: ("community", "communities"),
    CommunityInfo: ("community", "communities"),
    CommunitySummary: ("community", "communities"),
    PreparedDeleteCommunity: ("community", "communities"),
    ListEntity: ("list", "lists"),
    ListInfo: ("list", "lists"),
    ListSummary: ("list", "lists"),
    DeletedList: ("list", "lists"),
    AttributeEntity: ("attribute", "attributes"),
    AttributeInfo: ("attribute", "attributes"),
    AttributeSummary: ("attribute", "attributes"),
    PreparedDeleteAttribute: ("attribute", "attributes"),
    TaskEntity: ("task", "tasks"),
    PreparedDeleteTask: ("task", "tasks"),
}

ATTRIBUTE_TYPE_PREFIX_MAP = {
    AttributeType.STATIC: "static",
    AttributeType.TASK: "task",
    AttributeType.USER: "user",
}


def get_type_name_lower(
    mentionable: MentionableT | type[MentionableT], singular: bool
) -> str:
    mentionable_type = (
        mentionable if isinstance(mentionable, type) else type(mentionable)
    )

    type_str = TYPE_MAP[mentionable_type]

    if isinstance(mentionable, AttributeEntity):
        type_str = f"{ATTRIBUTE_TYPE_PREFIX_MAP[mentionable.type]} {type_str}"

    return type_str[not singular]


def get_instance_name(
    mentionable: MentionableT,
) -> str:
    if isinstance(mentionable, (MetaRank, CommunityRank, ServerRank)):
        return mentionable.name.title()

    return str(mentionable.name)


def type_name_for_body(
    mentionable: MentionableT | type[MentionableT], singular: bool = True
) -> _TaggedObj:
    return get_type_name_lower(mentionable, singular) @ T.RAW


def type_name_for_header(
    mentionable_type: type[MentionableT], singular: bool = True
) -> _TaggedObj:
    return get_type_name_lower(mentionable_type, singular).title() @ T.RAW


def mention_body(mentionable: MentionableT, singular: bool = True) -> _TaggedObj:
    return (
        f"{get_type_name_lower(type(mentionable), singular)} "
        f"``{get_instance_name(mentionable)}``"
    ) @ T.DEFAULT
