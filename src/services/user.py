from sqlalchemy.orm import Session

from domain.entities.community import CommunityEntity
from domain.entities.user import CommunityUserEntity, UserEntity
from domain.enums.rank import CommunityRank, MetaRank, ServerRank
from domain.value_objects.string import StrStore
from repositories.user import CommunityUserRepository, UserRepository
from db.models import CommunityUser
import typing as t

from services.services import Services


class UserService:
    def __init__(self, repo: UserRepository):
        self._repo = repo

    def get_or_create(
        self,
        user: UserEntity,
        *,
        overwrite_name: bool = True,
        overwrite_rank: bool = False,
    ) -> UserEntity:
        existing = self._repo.get_by_id(user.id)

        if existing is None:
            return self._repo.create(user)

        overwrite_any: bool = False

        if overwrite_name:
            existing.name = user.name
            overwrite_any = True

        if overwrite_rank:
            existing.rank = user.rank
            overwrite_any = True

        if not overwrite_any:
            return existing

        return self._repo.update(existing)


class CommunityUserService:
    def __init__(self, repo: CommunityUserRepository, user_service: UserService):
        self._repo = repo
        self._user_service = user_service

    def get_or_create(
        self,
        community_user: CommunityUserEntity,
        *,
        overwrite_rank: bool = False,
        overwrite_selected_list: bool = False,
    ) -> CommunityUserEntity:
        self._user_service.get_or_create(UserEntity(0, community_user.user.name))

        existing = self._repo.get_by_user_and_community_id(
            community_user.user, community_user.community_id
        )

        if existing is None:
            return self._repo.create(community_user)

        overwrite_any: bool = False

        if overwrite_rank:
            existing.rank = community_user.rank
            overwrite_any = True

        if overwrite_selected_list:
            existing.selected_list_id = community_user.selected_list_id
            overwrite_any = True

        if not overwrite_any:
            return existing

        return self._repo.update(existing)
