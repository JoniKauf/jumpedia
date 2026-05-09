import json
from db.models import Community
from domain.rank import CommunityRank
from repositories.community import CommunityRepository
from repositories.user import UserRepository
from domain.limits import Limits
from utils import text
from .base import BaseService
from sqlalchemy.orm import Session

class CommunityService(BaseService):
    def __init__(self, session: Session):
        self.session = session
        self.repo = CommunityRepository(session)
        self.user_repo = UserRepository(session)

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
        real_name = text.RealStr(name)
        norm_name = text.NormStr(real_name)
        
        del name

        # --- validation (business rules live HERE) ---
        if len(norm_name) > Limits.COMMUNITY_NAME_LENGTH_MAX:
            raise ValueError("community name too long")

        if self.repo.get_by_name(norm_name):
            raise ValueError("community already exists")

        # --- create community ---
        community = self.repo.create(
            norm_name,
            real_name,
            limits,
        )

        # --- link server ---
        self.repo.link_server(community.community_id, server_id)

        # --- ensure owner exists in community system ---
        self.user_repo.create_user_and_community_user(
            user_id=owner_id,
            norm_name=text.NormStr(owner_name),
            raw_name=owner_name,
            community_id=community.community_id,
            community_rank=CommunityRank.OWNER,
        )

        return community

    # -------------------------
    # DELETE COMMUNITY
    # -------------------------
    def delete_community(self, community_id: int):
        self.repo.delete(community_id)