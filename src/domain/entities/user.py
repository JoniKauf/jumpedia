from dataclasses import dataclass

from domain.entities.base import BaseEntity
from domain.enums.rank import CommunityRank, JumpediaRank
from domain.value_objects.strings import StrStore

@dataclass(kw_only=True, slots=True)
class UserEntity(BaseEntity):
    _name: StrStore
    _rank: JumpediaRank

    @property
    def name(self) -> StrStore:
        return self._name

    @property
    def rank(self) -> JumpediaRank:
        return self._rank


@dataclass(slots=True)
class CommunityUserEntity(BaseEntity):
    _community_id: int
    _user: UserEntity
    _rank: CommunityRank

    @property
    def community_id(self) -> int:
        return self._community_id

    @property
    def user(self) -> UserEntity:
        return self._user

    @property
    def rank(self) -> CommunityRank:
        return self._rank