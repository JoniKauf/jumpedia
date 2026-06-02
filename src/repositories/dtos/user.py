from dataclasses import dataclass

from domain.enums.rank import CommunityRank, MetaRank
from domain.types.id import ID
from domain.value_objects.string import StrStore
from domain.entities.user import UserEntity


@dataclass(frozen=True, slots=True)
class CreateUserDTO:
    id: ID
    name: StrStore
    rank: MetaRank = MetaRank.DEFAULT


@dataclass(frozen=True, slots=True)
class CreateCommunityUserDTO:
    user: UserEntity
    community_id: ID
    rank: CommunityRank = CommunityRank.DEFAULT
    selected_list_id: ID | None = None
