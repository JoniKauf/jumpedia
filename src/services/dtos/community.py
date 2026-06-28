from dataclasses import dataclass
from datetime import datetime

from domain.entities.community_user import CommunityUserEntity
from domain.entities.list import ListEntity
from domain.value_objects.community import CommunityLimits, CommunityNameStr
from domain.value_objects.string import Str


@dataclass(frozen=True, slots=True)
class CommunityInfo:
    name: CommunityNameStr
    default_selected_list: ListEntity | None
    created: datetime
    limits: CommunityLimits
    community_users: tuple[CommunityUserEntity, ...]
    lists: tuple[ListEntity, ...]
    total_task_count: int


@dataclass(frozen=True, slots=True)
class CommunitySummary:
    name: CommunityNameStr
    created: datetime
    community_user_count: int
    list_count: int
    total_task_count: int


@dataclass(frozen=True, slots=True)
class DeletedCommunity:
    name: Str
    created: datetime
    limits: CommunityLimits
