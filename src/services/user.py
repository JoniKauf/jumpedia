from sqlalchemy.orm import Session

from domain.entities.community import CommunityEntity
from domain.entities.user import CommunityUserEntity, UserEntity
from domain.enums.rank import CommunityRank, MetaRank, ServerRank
from domain.value_objects.string import StrStore
from repositories.user import CommunityUserRepository, UserRepository
from db.models import CommunityUser
import typing as t


class UserService:
    def __init__(self, session: Session):
        self.user_repo = UserRepository(session)

    def get_or_create(
        self,
        user: UserEntity,
        *,
        overwrite_name: bool = True,
        overwrite_rank: bool = False,
    ) -> UserEntity:
        existing = self.user_repo.get_by_id(user.id)

        if existing is None:
            return self.user_repo.create(user)

        overwrite_any: bool = False

        if overwrite_name:
            existing.name = user.name
            overwrite_any = True

        if overwrite_rank:
            existing.rank = user.rank
            overwrite_any = True

        if not overwrite_any:
            return existing

        return self.user_repo.update(existing)


class CommunityUserService:
    def __init__(self, session: Session):
        self.community_user_repo = CommunityUserRepository(session)

    def get_or_create(
        self,
        community_user: CommunityUserEntity,
        *,
        overwrite_rank: bool = False,
        overwrite_selected_list: bool = False,
    ) -> CommunityUserEntity:
        existing = self.community_user_repo.get_by_user_id_and_community_id(
            community_user.user_id, community_user.community_id
        )

        if existing is None:
            return self.community_user_repo.create(community_user)

        overwrite_any: bool = False

        if overwrite_rank:
            existing.rank = community_user.rank
            overwrite_any = True

        if overwrite_selected_list:
            existing.selected_list_id = community_user.selected_list_id
            overwrite_any = True

        if not overwrite_any:
            return existing

        return self.community_user_repo.update(existing)
