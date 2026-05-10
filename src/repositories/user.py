from sqlalchemy.sql import select

from db.models import User, CommunityUser
from domain.enums.rank import CommunityRank, JumpediaRank
from domain.value_objects.s import StrStore
from .base import BaseRepository

class UserRepository(BaseRepository):
    def get_user(self, *, user_id: int) -> User | None:
        return self.session.get(User, user_id)
    
    def get_community_user(self, *, user_id: int, community_id: int) -> CommunityUser | None:
        stmt = select(CommunityUser).where(
            CommunityUser.user_id == user_id,
            CommunityUser.community_id == community_id,
        )

        return self.session.execute(stmt).scalar_one_or_none()
    
    def create_user(self, *, user_id: int, name: StrStore, rank: JumpediaRank) -> User:
        obj = User(
            user_id=user_id,
            norm_name=name.norm,
            raw_name=name.raw,
            power=rank,
        )

        self.session.add(obj)
        self.session.flush()

        return obj
    
    def create_community_user(self, *, user_id: int, community_id: int, rank: CommunityRank, selected_list_id: int | None) -> CommunityUser:
        obj = CommunityUser(
            user_id=user_id,
            community_id=community_id,
            power=rank,
            selected_list_id=selected_list_id
        )

        self.session.add(obj)
        self.session.flush()

        return obj