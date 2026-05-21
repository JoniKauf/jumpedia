import json
from db.models import Community
from domain import errors
from domain.entities.community import CommunityEntity
from domain.entities.user import CommunityUserEntity, UserEntity
from domain.enums.rank import CommunityRank, MetaRank, ServerRank
from domain.value_objects.string import StrStore
from interfaces.context.interacting_user import InteractingUserContext
from repositories.community import CommunityRepository
from repositories.user import UserRepository
from domain.value_objects.limits import Limits
from services._permission import PermissionService
from services.dtos.community import DeletedCommunityDTO
from services.list import ListService
from services.user import CommunityUserService, UserService
from sqlalchemy.orm import Session


class CommunityService:
    def __init__(self, session: Session):
        self.community_repo = CommunityRepository(session)
        self.community_user_service = CommunityUserService(session)
        self.list_service = ListService(session)
        self.user_service = UserService(session)

    def _get_by_server_id_or_raise(self, server_id: int) -> CommunityEntity:
        obj = self.community_repo.get_by_server_id(server_id)

        if obj is None:
            raise errors.NotInCommunity
        
        return obj
    
    def _get_by_server_id_or_raise_and_community_user(self, server_id: int, user: UserEntity) -> tuple[CommunityEntity, CommunityUserEntity]:
        community = self._get_by_server_id_or_raise(server_id)
        community_user = self.community_user_service.get_or_create(CommunityUserEntity(0, community.id, user.id))

        return community, community_user
    
    # -------------------------
    # CREATE COMMUNITY
    # -------------------------
    def create(
        self,
        ctx: InteractingUserContext,
        name: StrStore,
        owner_id: int,
        owner_name: StrStore,
        limits: Limits,
    ) -> CommunityEntity:
        user = self.user_service.get_or_create(UserEntity(ctx.id, ctx.name))

        PermissionService.ensure_meta_rank(user.rank, MetaRank.ADMINISTRATOR)

        existing = self.community_repo.get_by_name(name)

        if existing is not None:
            raise errors.NameAlreadyTaken(name, existing)
        
        existing = self.community_repo.get_by_server_id(ctx.server_id)

        if existing is not None:
            raise errors.ServerAlreadyConnectedToACommunity(ctx.server_id, existing)
        
        del existing

        community = self.community_repo.create(CommunityEntity(0, name, limits))

        self.community_repo.link_server(community, ctx.server_id)

        self.community_user_service.get_or_create(
            CommunityUserEntity(0, community.id, owner_id, CommunityRank.OWNER, None),
            overwrite_rank=True,
            overwrite_selected_list=True,
        )

        self.list_service.create(community.id, StrStore("Main"))

        return community

    # -------------------------
    # DELETE COMMUNITY
    # -------------------------
    def delete(self, ctx: InteractingUserContext) -> DeletedCommunityDTO:
        user = self.user_service.get_or_create(UserEntity(ctx.id, ctx.name))

        community, community_user = self._get_by_server_id_or_raise_and_community_user(ctx.server_id, user)

        PermissionService.ensure_community_rank(community_user.rank, user.rank, CommunityRank.OWNER)

        self.community_repo.delete(community.id)

        return DeletedCommunityDTO(community.name, community.limits)
