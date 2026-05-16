from sqlalchemy import select

from db.models import User, CommunityUser
from domain.entities.user import CommunityUserEntity, UserEntity
from domain.enums.rank import CommunityRank, MetaRank
from domain.value_objects.strings import RealStr, StrStore
from .base import BaseRepository
import typing as t

def _user_model_to_entity(model: User) -> UserEntity:
    return UserEntity(
        _id=model.user_id,
        _name=StrStore(_real=RealStr(model.raw_name), _norm=model.norm_name),
        _rank=MetaRank(model.power)
    )

def _community_user_model_to_entity(model: CommunityUser) -> CommunityUserEntity:
    return CommunityUserEntity(
        _id=model.community_user_id,
        _community_id=model.community_id,
        _rank=CommunityRank(model.power)
    )

class UserRepository(BaseRepository):
    def get_by_id(self, user_id: int) -> UserEntity | None:
        obj = self.session.get(User, user_id)
        return None if obj is None else _user_model_to_entity(obj)

    def create(self, user_id: int, name: StrStore, rank: MetaRank) -> UserEntity:
        obj = User(
            user_id=user_id,
            norm_name=name.norm,
            raw_name=name.raw,
            power=rank,
        )

        self.session.add(obj)
        self.session.flush()

        return _user_model_to_entity(obj)


class CommunityUserRepository(BaseRepository):
    def get_by_user_id_and_community_id(self, user_id: int, community_id: int) -> CommunityUserEntity | None:
        stmt = select(CommunityUser).where(
            CommunityUser.user_id == user_id,
            CommunityUser.community_id == community_id,
        )
        obj = self.session.scalar(stmt)
        return None if obj is None else _community_user_model_to_entity(obj)

    def create(
        self,
        user_id: int,
        community_id: int,
        rank: CommunityRank,
        selected_list_id: int | None,
    ) -> CommunityUserEntity:
        obj = CommunityUser(
            user_id=user_id,
            community_id=community_id,
            power=rank,
            selected_list_id=selected_list_id,
        )

        self.session.add(obj)
        self.session.flush()

        return _community_user_model_to_entity(obj)