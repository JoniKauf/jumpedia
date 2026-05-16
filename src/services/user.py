from sqlalchemy.orm import Session

from domain.entities.user import CommunityUserEntity, UserEntity
from domain.enums.rank import CommunityRank, MetaRank, ServerRank
from domain.value_objects.strings import StrStore
from repositories.user import CommunityUserRepository, UserRepository
from db.models import CommunityUser
import typing as t

class UserService:
    def __init__(self, session: Session):
        self.user_repo = UserRepository(session)

    def get_or_create_user(
        self,
        user_id: int,
        name: StrStore,
        rank: MetaRank = MetaRank.DEFAULT,
        *,
        overwrite_name: bool = True,
        overwrite_rank: bool = False,
    ) -> UserEntity:
        user = self.user_repo.get_by_id(user_id=user_id)

        if user is None:
            return self.user_repo.create(
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

        return user
    

class CommunityUserService:
    def __init__(self, session: Session):
        self.community_user_repo = CommunityUserRepository(session)

    def get_or_create_community_user(
        self,
        user_id: int,
        community_id: int,
        rank: CommunityRank = CommunityRank.DEFAULT,
        selected_list_id: int | None = None
    ) -> CommunityUserEntity:
        community_user = self.community_user_repo.get_by_user_id_and_community_id(user_id=user_id, community_id=community_id)

        if community_user is not None:
            return community_user
        
        return self.community_user_repo.create(
            user_id=user_id,
            community_id=community_id,
            rank=rank,
            selected_list_id=selected_list_id
        )
    
        