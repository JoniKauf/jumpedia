from dataclasses import dataclass

from domain.enums.rank import CommunityRank, JumpediaRank
from domain.value_objects.strings import StrStore

@dataclass(frozen=True, unsafe_hash=True, slots=True)
class UserEntity:
    user_id: int
    name: StrStore
    rank: JumpediaRank


@dataclass(frozen=True, unsafe_hash=True, slots=True)
class CommunityUserEntity:
    community_user_id: int
    community_id: int
    user: UserEntity
    rank: CommunityRank