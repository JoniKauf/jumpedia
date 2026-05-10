from sqlalchemy.orm import Session

from domain.enums.rank import CommunityRank, JumpediaRank
from domain.value_objects.s import StrStore
from repositories.user import UserRepository
from db.models import CommunityUser
from services.base import BaseService

class UserService(BaseService):
    def __init__(self, session: Session):
        self.session = session
        self.user_repo = UserRepository(session)

    def get_or_create_user(
        self,
        user_id: int,
        name: StrStore,
        rank: JumpediaRank = JumpediaRank.DEFAULT,
        *,
        overwrite_name: bool = True,
        overwrite_rank: bool = False,
    ):
        user = self.user_repo.get_user(user_id=user_id)

        if user is None:
            return self.user_repo.create_user(
                user_id=user_id,
                name=name,
                rank=rank,
            )

        updated = False

        if overwrite_name:
            user.norm_name = name.norm
            user.raw_name = name.raw
            updated = True

        if overwrite_rank:
            user.power = rank
            updated = True

        if updated:
            self.session.flush()

        return user

    def get_or_create_community_user(
        self,
        user_id: int,
        community_id: int,
        name: StrStore,
        rank: CommunityRank = CommunityRank.DEFAULT,
        selected_list_id: int | None = None
    ) -> CommunityUser:
        _ = self.get_or_create_user(
            user_id, 
            name,
        )

        community_user = self.user_repo.get_community_user(user_id=user_id, community_id=community_id)

        if community_user is None:
            return self.user_repo.create_community_user(
                user_id=user_id,
                community_id=community_id,
                rank=rank,
                selected_list_id=selected_list_id
            )
        
        return community_user