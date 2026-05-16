from dataclasses import dataclass

from domain.entities.base import BaseEntity
from domain.enums.rank import CommunityRank, MetaRank
from domain.value_objects.strings import StrStore

@dataclass(slots=True)
class UserEntity(BaseEntity):
    _name: StrStore
    _rank: MetaRank

    @property
    def name(self) -> StrStore:
        return self._name

    @property
    def rank(self) -> MetaRank:
        return self._rank


@dataclass(slots=True)
class CommunityUserEntity(BaseEntity):
    _community_id: int
    _rank: CommunityRank

    @property
    def community_id(self) -> int:
        return self._community_id

    @property
    def rank(self) -> CommunityRank:
        return self._rank