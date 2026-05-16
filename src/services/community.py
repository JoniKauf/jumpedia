import json
from db.models import Community
from domain.entities.community import CommunityEntity
from domain.entities.user import UserEntity
from domain.enums.rank import CommunityRank, MetaRank, ServerRank
from domain.value_objects import strings
from interfaces.list import StrStore
from repositories.community import CommunityRepository
from repositories.user import UserRepository
from domain.value_objects.limits import Limits
from services._permission import PermissionService
from services.user import UserService
from .base import BaseService
from sqlalchemy.orm import Session

class CommunityService(BaseService):
    def __init__(self, session: Session):
        self.community_repo = CommunityRepository(session)

    # -------------------------
    # CREATE COMMUNITY
    # -------------------------
    def create_community(
        self,
        name: StrStore,
        server_id: int,
        owner: UserEntity,
        owner_server_rank: ServerRank,
        limits: Limits
    ) -> Community:
        PermissionService.ensure_meta_rank(owner.rank, MetaRank.ADMINISTRATOR)

        community = CommunityEntity(None, name, limits)

        # --- create community ---
        community = self.community_repo.create(
            norm_name,
            real_name,
            limits,
        )

        # --- link server ---
        self.community_repo.link_server(community.community_id, server_id)

        # --- ensure owner exists in community system ---
        self.user_repo.ensure_user_and_community_user(
            user_id=owner_id,
            name=strings.StrStore(owner_name),
            community_id=community.community_id,
            community_rank=CommunityRank.OWNER,
        )

        return community

    # -------------------------
    # DELETE COMMUNITY
    # -------------------------
    def delete_community(self, community_id: int):
        self.community_repo.delete(community_id)

    def _get_community_by_server_id_or_throw(self, server_id: int) -> CommunityEntity:
        community = self.community_repo.get_by_server_id(server_id)

        if community is None:
            raise errors.NotInCommunity()
        
        return community