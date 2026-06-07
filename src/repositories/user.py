from sqlalchemy import func, select

from db.models import User, CommunityUser
from domain.entities.user import CommunityUserEntity, UserEntity
from domain.enums.rank import CommunityRank, MetaRank
from domain.types.id import ID
from domain.value_objects.string import RealStr, StrStore
from repositories.dtos.user import CreateCommunityUserDTO, CreateUserDTO
from .base import BaseRepository
import typing as t


def _user_model_to_entity(model: User) -> UserEntity:
    return UserEntity(
        id=model.user_id,
        name=StrStore(_real=RealStr(model.raw_name), _norm=model.norm_name),
        rank=MetaRank(model.power),
    )


def _community_user_model_to_entity(
    model: CommunityUser, user: UserEntity
) -> CommunityUserEntity:
    return CommunityUserEntity(
        id=model.community_user_id,
        user=user,
        community_id=model.community_id,
        rank=CommunityRank(model.power),
        selected_list_id=model.selected_list_id,
    )


class UserRepository(BaseRepository):
    def get_by_id(self, user_id: int) -> UserEntity | None:
        obj = self.session.get(User, user_id)
        return None if obj is None else _user_model_to_entity(obj)

    def create(self, user: CreateUserDTO) -> UserEntity:
        obj = User(
            user_id=user.id,
            norm_name=user.name.norm,
            raw_name=user.name.raw,
            power=user.rank.value,
        )

        self.session.add(obj)
        self.session.flush()

        return _user_model_to_entity(obj)

    def update(
        self,
        user: UserEntity,
    ) -> UserEntity:
        obj = self.session.get(User, user.id)

        if obj is None:
            raise RuntimeError("Tried updating a non existant user")

        obj.raw_name = user.name.raw
        obj.norm_name = user.name.norm
        obj.power = user.meta_rank.value

        return _user_model_to_entity(obj)


class CommunityUserRepository(BaseRepository):
    def get_by_user_and_community_id(
        self, user: UserEntity, community_id: int
    ) -> CommunityUserEntity | None:
        stmt = select(CommunityUser).where(
            CommunityUser.user_id == user.id,
            CommunityUser.community_id == community_id,
        )
        obj = self.session.scalar(stmt)
        return None if obj is None else _community_user_model_to_entity(obj, user)

    def create(self, community_user: CreateCommunityUserDTO) -> CommunityUserEntity:
        obj = CommunityUser(
            user_id=community_user.user.id,
            community_id=community_user.community_id,
            power=community_user.rank.value,
            selected_list_id=community_user.selected_list_id,
        )

        self.session.add(obj)
        self.session.flush()

        return _community_user_model_to_entity(obj, community_user.user)

    def update(
        self,
        community_user: CommunityUserEntity,
    ) -> CommunityUserEntity:
        obj = self.session.get(CommunityUser, community_user.id)

        if obj is None:
            raise RuntimeError("Tried updating a non existant community user")

        obj.power = community_user.community_rank.value
        obj.selected_list_id = community_user.selected_list_id

        return _community_user_model_to_entity(obj, community_user.user)

    def count_grouped_by_community_id(self) -> dict[ID, int]:
        stmt = (
            select(
                CommunityUser.community_id,
                func.count()
            )
            .group_by(CommunityUser.community_id)
        )

        return {
            community_id: count
            for community_id, count in self.session.execute(stmt)
        }
        
    def get_all_by_community_id(self, community_id: int) -> list[CommunityUserEntity]:
        stmt = (
            select(CommunityUser, User)
            .join(User, User.user_id == CommunityUser.user_id)
            .where(CommunityUser.community_id == community_id)
        )

        return [
            _community_user_model_to_entity(
                community_user,
                _user_model_to_entity(user),
            )
            for community_user, user in self.session.execute(stmt)
        ]

    def count_by_community_id(self, community_id: int) -> int:
        stmt = (
            select(func.count())
            .select_from(CommunityUser)
            .where(CommunityUser.community_id == community_id)
        )
        return self.session.scalar(stmt) or 0
