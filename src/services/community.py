import json
from db.models import Community
from domain import errors
from domain.entities.community import CommunityEntity
from domain.entities.user import CommunityUserEntity, UserEntity
from domain.enums.rank import CommunityRank, MetaRank, ServerRank
from domain.types.id import ID
from domain.value_objects.string import StrStore
from interfaces.contexts.interacting_user import InteractingUserContext
from repositories.community import CommunityRepository
from repositories.dtos.community import CreateCommunityDTO
from repositories.dtos.user import CreateCommunityUserDTO
from repositories.list import ListRepository
from repositories.user import UserRepository
from domain.value_objects.limits import Limits
from services._permission import PermissionService
from services.dtos.community import DeletedCommunityDTO
from services.list import ListService
from services.user import CommunityUserService, UserService
from sqlalchemy.orm import Session


class CommunityService:
    def __init__(self, session: Session):
        self._community_repo = CommunityRepository(session)
        self._community_user_service = CommunityUserService(session)
        self._list_repo = ListRepository(session)
        self._list_service = ListService(session)
        self._user_service = UserService(session)

    def _get_by_server_id_or_raise(self, server_id: int) -> CommunityEntity:
        obj = self._community_repo.get_by_server_id(server_id)

        if obj is None:
            raise errors.NotInCommunity

        return obj

    def _get_by_server_id_or_raise_and_community_user(
        self, server_id: int, user: UserEntity
    ) -> tuple[CommunityEntity, CommunityUserEntity]:
        community = self._get_by_server_id_or_raise(server_id)
        community_user = self._community_user_service._get_or_create(
            CreateCommunityUserDTO(user, community.id)
        )

        return community, community_user

    def info(
        self,
        ctx: InteractingUserContext,
    ):
        community, _ = self._get_by_server_id_or_raise_and_community_user(ctx.server_id, ctx.user)

        lists = self._list_repo.get_all(community.id)
        community_users = self._community_repo.create

    # -------------------------
    # CREATE COMMUNITY
    # -------------------------
    def create(
        self,
        ctx: InteractingUserContext,
        name: StrStore,
        owner_id: ID,
        owner_name: StrStore,
        limits: Limits,
    ) -> CommunityEntity:
        PermissionService.ensure_meta_rank(ctx.user.meta_rank, MetaRank.ADMINISTRATOR)

        existing = self._community_repo.get_by_name(name)

        if existing is not None:
            raise errors.NameAlreadyTaken(name, existing)

        existing = self._community_repo.get_by_server_id(ctx.server_id)

        if existing is not None:
            raise errors.ServerAlreadyConnectedToACommunity(ctx.server_id, existing)

        del existing

        community = self._community_repo.create(CreateCommunityDTO(name, limits))

        self._community_repo.link_server(community, ctx.server_id)

        self._community_user_service._get_or_create(
            CreateCommunityUserDTO(UserEntity(owner_id, owner_name), community.id, CommunityRank.OWNER, None),
            overwrite_rank=True,
            overwrite_selected_list=True,
        )

        # TODO set as default
        self._list_service.create(community.id, StrStore("Main"))

        return community

    # -------------------------
    # DELETE COMMUNITY
    # -------------------------
    def delete(self, ctx: InteractingUserContext) -> DeletedCommunityDTO:
        community, community_user = self._get_by_server_id_or_raise_and_community_user(
            ctx.server_id, ctx.user
        )

        PermissionService.ensure_community_rank(
            community_user.community_rank, ctx.user.meta_rank, CommunityRank.OWNER
        )

        self._community_repo.delete(community.id)

        return DeletedCommunityDTO(community.name, community.limits)
