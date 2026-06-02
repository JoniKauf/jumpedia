from dataclasses import dataclass

from domain.entities.list import ListEntity
from domain.entities.user import CommunityUserEntity
from domain.types.id import ID
from domain.value_objects.community import CommunityName
from domain.value_objects.limits import Limits
from domain.value_objects.string import StrStore


@dataclass(frozen=True, slots=True)
class DeletedCommunityDTO:
    name: StrStore
    limits: Limits


@dataclass(frozen=True, slots=True)
class CommunityInfoDTO:
    name: CommunityName
    limits: Limits
    default_selected_list_id: int | None
    community_users: tuple[CommunityUserEntity, ...]
    lists: tuple[ListEntity, ...]
    task_count: int
