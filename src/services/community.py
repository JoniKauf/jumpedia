import json
from db.models import Community
from domain import errors
from domain.entities.community import CommunityEntity
from domain.entities.user import CommunityUserEntity, UserEntity
from domain.enums.rank import CommunityRank, MetaRank, ServerRank
from domain.value_objects.string import StrStore
from repositories.community import CommunityRepository
from repositories.user import UserRepository
from domain.value_objects.limits import Limits
from services._permission import PermissionService
from services.dto.community import DeletedCommunityDTO
from services.list import ListService
from services.user import CommunityUserService, UserService
from sqlalchemy.orm import Session


class CommunityService:
    def __init__(self, session: Session):
        self.community_repo = CommunityRepository(session)
        self.community_user_service = CommunityUserService(session)
        self.list_service = ListService(session)

    def _get_by_server_id_or_raise(self, server_id: int) -> CommunityEntity:
        obj = self.community_repo.get_by_server_id(server_id)

        if obj is None:
            raise errors.NotFound(CommunityEntity)
        
        return obj
    
    def _get_by_server_id_or_raise_and_community_user(self, server_id: int, user: UserEntity) -> tuple[CommunityEntity, CommunityUserEntity]:
        community = self._get_by_server_id_or_raise(server_id)
        return community, self.community_user_service.get_or_create(CommunityUserEntity(0, community.id, user.id))

    # -------------------------
    # CREATE COMMUNITY
    # -------------------------
    def create(
        self,
        user: UserEntity,
        name: StrStore,
        server_id: int,
        owner: UserEntity,
        limits: Limits,
    ) -> CommunityEntity:
        PermissionService.ensure_meta_rank(user.rank, MetaRank.ADMINISTRATOR)

        existing = self.community_repo.get_by_name(name)

        if existing is not None:
            raise errors.NameAlreadyTaken(name, existing)
        
        existing = self.community_repo.get_by_server_id(server_id)

        if existing is not None:
            raise errors.ServerAlreadyConnectedToACommunity(server_id, existing)
        
        del existing

        community = self.community_repo.create(CommunityEntity(0, name, limits))

        self.community_repo.link_server(community, server_id)

        self.community_user_service.get_or_create(
            CommunityUserEntity(0, community.id, owner.id, CommunityRank.OWNER, None),
            overwrite_rank=True,
            overwrite_selected_list=True,
        )

        self.list_service

        return community

    # -------------------------
    # DELETE COMMUNITY
    # -------------------------
    def delete(self, user: UserEntity, server_id: int) -> DeletedCommunityDTO:
        community, community_user = self._get_by_server_id_or_raise_and_community_user(server_id, user)

        PermissionService.ensure_community_rank(community_user.rank, user.rank, CommunityRank.OWNER)

        self.community_repo.delete(community.id)

        return DeletedCommunityDTO(community.name, community.limits)

    def _get_community_by_server_id_or_throw(self, server_id: int) -> CommunityEntity:
        community = self.community_repo.get_by_server_id(server_id)

        if community is None:
            raise errors.NotInCommunity()

        return community
