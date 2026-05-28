from dataclasses import dataclass

from domain.entities.base import BaseEntity
from domain.enums.rank import CommunityRank, MetaRank
from domain.types.id import ID
from domain.value_objects.string import StrStore

class UserEntity(BaseEntity):
    def __init__(
        self, id: ID, name: StrStore, rank: MetaRank = MetaRank.DEFAULT
    ) -> None:
        super().__init__(id)

        self.name = name
        self.meta_rank = rank

    @property
    def name(self) -> StrStore:
        return self._name

    @name.setter
    def name(self, value: StrStore) -> None:
        self._name = value

    @property
    def meta_rank(self) -> MetaRank:
        return self._rank

    @meta_rank.setter
    def meta_rank(self, value: MetaRank) -> None:
        self._rank = value


class CommunityUserEntity(BaseEntity):
    def __init__(
        self,
        id: ID,
        user: UserEntity,
        community_id: ID,
        rank: CommunityRank = CommunityRank.DEFAULT,
        selected_list_id: ID | None = None,
    ) -> None:
        super().__init__(id)

        self._community_id = community_id
        self.community_rank = rank
        self.selected_list_id = selected_list_id
        self.user = user

    @property
    def community_id(self) -> ID:
        return self._community_id

    @property
    def community_rank(self) -> CommunityRank:
        return self._rank

    @community_rank.setter
    def community_rank(self, value: CommunityRank) -> None:
        self._rank = value

    @property
    def selected_list_id(self) -> ID | None:
        return self._selected_list_id

    @selected_list_id.setter
    def selected_list_id(self, value: ID | None) -> None:
        self._selected_list_id = value

    @property
    def user(self) -> UserEntity:
        return self._user

    @user.setter
    def user(self, value: UserEntity) -> None:
        self._user = value