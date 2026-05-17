from dataclasses import dataclass

from domain.entities.base import BaseEntity
from domain.enums.rank import CommunityRank, MetaRank
from domain.value_objects.string import StrStore


class UserEntity(BaseEntity):
    def __init__(
        self, id: int, name: StrStore, rank: MetaRank = MetaRank.DEFAULT
    ) -> None:
        super().__init__(id)
        self.name = name
        self.rank = rank

    @property
    def name(self) -> StrStore:
        return self._name

    @name.setter
    def name(self, value: StrStore) -> None:
        self._name = value

    @property
    def rank(self) -> MetaRank:
        return self._rank

    @rank.setter
    def rank(self, value: MetaRank) -> None:
        self._rank = value


class CommunityUserEntity(BaseEntity):
    def __init__(
        self,
        id: int,
        community_id: int,
        user_id: int,
        rank: CommunityRank = CommunityRank.DEFAULT,
        selected_list_id: int | None = None,
    ) -> None:
        super().__init__(id)
        self._community_id = community_id
        self._user_id = user_id
        self.rank = rank
        self.selected_list_id = selected_list_id

    @property
    def community_id(self) -> int:
        return self._community_id

    @property
    def user_id(self) -> int:
        return self._user_id

    @property
    def rank(self) -> CommunityRank:
        return self._rank

    @rank.setter
    def rank(self, value: CommunityRank) -> None:
        self._rank = value

    @property
    def selected_list_id(self) -> int | None:
        return self._selected_list_id

    @selected_list_id.setter
    def selected_list_id(self, value: int | None) -> None:
        self._selected_list_id = value
