from dataclasses import dataclass
from datetime import datetime

from domain.entities.list import ListEntity
from domain.entities.user import CommunityUserEntity
from domain.types.id import ID
from domain.value_objects.community import CommunityName
from domain.value_objects.community import CommunityLimits
from domain.value_objects.string import StrStore


@dataclass(frozen=True, slots=True)
class CommunityInfoDTO:
    name: CommunityName
    default_selected_list: ListEntity | None
    created: datetime
    limits: CommunityLimits
    community_users: tuple[CommunityUserEntity, ...]
    lists: tuple[ListEntity, ...]
    total_task_count: int

@dataclass(frozen=True, slots=True)
class CommunitySummaryDTO:
    name: CommunityName
    created: datetime
    community_user_count: int
    list_count: int
    total_task_count: int

@dataclass(frozen=True, slots=True)
class DeletedCommunityDTO:
    name: StrStore
    created: datetime
    limits: CommunityLimits