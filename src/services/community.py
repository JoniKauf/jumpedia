import json
from db.models import Community
from domain.enums.rank import CommunityRank
from domain.value_objects import strings
from repositories.community import CommunityRepository
from repositories.user import UserRepository
from domain.value_objects.limits import Limits
from .base import BaseService
from sqlalchemy.orm import Session

class CommunityService(BaseService):
    def __init__(self, session: Session):
        super().__init__(session)
        
        self.user_repo = UserRepository(session)

    def get_by_server_id(self, server_id: int) -> Community | None:
        return self.community_repo.get_by_server_id(server_id)
    
    # -------------------------
    # CREATE COMMUNITY
    # -------------------------
    def create_community(
        self,
        name: str,
        server_id: int,
        owner_id: int,
        owner_name: str,
        limits: Limits
    ) -> Community:
        real_name = strings.RealStr(name)
        norm_name = strings.NormStr(real_name)
        
        del name

        # --- validation (business rules live HERE) ---
        if len(norm_name) > Limits.COMMUNITY_NAME_LENGTH_MAX:
            raise ValueError("community name too long")

        if self.community_repo.get_by_name(norm_name):
            raise ValueError("community already exists")

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