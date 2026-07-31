from dataclasses import dataclass
from datetime import datetime

from jumpedia.domain.entities.community import CommunityEntity
from jumpedia.domain.entities.list import ListEntity
from jumpedia.domain.entities.member import MemberEntity
from jumpedia.domain.typing.community import CommunityID
from jumpedia.domain.value_objects.community import CommunityLimits, CommunityNameStr
from jumpedia.domain.value_objects.datetime import DateTimeWrapper


@dataclass(frozen=True, slots=True)
class CommunityInfo:
    community: CommunityEntity
    default_selected_list: ListEntity | None
    members: tuple[MemberEntity, ...]
    lists: tuple[ListEntity, ...]
    total_task_count: int


@dataclass(frozen=True, slots=True)
class CommunitySummary:
    name: CommunityNameStr
    created: DateTimeWrapper
    member_count: int
    list_count: int
    total_task_count: int


@dataclass(frozen=True, slots=True)
class PreparedDeleteCommunity:
    community_id: CommunityID
