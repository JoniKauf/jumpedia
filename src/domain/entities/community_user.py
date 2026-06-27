from dataclasses import dataclass

from domain.entities.base import BaseEntity
from domain.entities.user import UserEntity
from domain.enums.rank import CommunityRank, MetaRank
from domain.types.community import CommunityID
from domain.types.community_user import CommunityUserID
from domain.types.list import ListID
from domain.value_objects.string import Str


class CommunityUserEntity(BaseEntity[CommunityUserID]):
    def __init__(
        self,
        community_user_id: CommunityUserID,
        user: UserEntity,
        community_id: CommunityID,
        rank: CommunityRank = CommunityRank.DEFAULT,
        selected_list_id: ListID | None = None,
    ) -> None:
        super().__init__(community_user_id)

        self._community_id = community_id
        self.community_rank = rank
        self.selected_list_id = selected_list_id
        self.user = user

    @property
    def community_user_id(self) -> CommunityUserID:
        return self._composite_key[0]
    
    @property
    def community_id(self) -> CommunityID:
        return self._community_id

    @property
    def community_rank(self) -> CommunityRank:
        return self._rank

    @community_rank.setter
    def community_rank(self, value: CommunityRank) -> None:
        self._rank = value

    @property
    def selected_list_id(self) -> ListID | None:
        return self._selected_list_id

    @selected_list_id.setter
    def selected_list_id(self, value: ListID | None) -> None:
        self._selected_list_id = value

    @property
    def user(self) -> UserEntity:
        return self._user

    @user.setter
    def user(self, value: UserEntity) -> None:
        self._user = value

    @property
    def name(self) -> Str:
        return self.user.name

    @property
    def meta_rank(self) -> MetaRank:
        return self.user.meta_rank
