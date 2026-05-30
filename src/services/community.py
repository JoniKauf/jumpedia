from dataclasses import dataclass
from domain import errors
from domain.entities.community import CommunityEntity
from domain.entities.user import CommunityUserEntity, UserEntity
from domain.enums.rank import CommunityRank, MetaRank
from domain.types.id import ID
from domain.value_objects.string import StrStore
from interfaces.contexts.interacting_user import InteractingUserContext
from repositories.community import CommunityRepository
from repositories.dtos.community import CreateCommunityDTO
from repositories.dtos.user import CreateCommunityUserDTO
from domain.value_objects.limits import Limits
from services.permission import PermissionService
from services.dtos.community import DeletedCommunityDTO
from services.list import ListService
from services.user import CommunityUserService

@dataclass(frozen=True, slots=True, eq=False)
class CommunityService:
    _repo: CommunityRepository
    _query_service: CommunityQueryService
    _permission_service: PermissionService
    _community_user_service: CommunityUserService
    _list_service: ListService

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
        self._permission_service.ensure_meta_rank(ctx.user.meta_rank, MetaRank.ADMINISTRATOR)

        existing = self._repo.get_by_name(name)

        if existing is not None:
            raise errors.NameAlreadyTaken(name, existing)

        existing = self._repo.get_by_server_id(ctx.server_id)

        if existing is not None:
            raise errors.ServerAlreadyConnectedToACommunity(ctx.server_id, existing)

        del existing

        community = self._repo.create(CreateCommunityDTO(name, limits))

        self._repo.link_server(community, ctx.server_id)

        self._community_user_service.get_or_create(
            CreateCommunityUserDTO(UserEntity(owner_id, owner_name), community.id, CommunityRank.OWNER, None),
            overwrite_rank=True,
            overwrite_selected_list=True,
        )

        # TODO set as default
        self._list_service.create(ctx, StrStore("Main"))

        return community

    # -------------------------
    # DELETE COMMUNITY
    # -------------------------
    def delete(self, ctx: InteractingUserContext) -> DeletedCommunityDTO:
        community, community_user = self._query_service.get_by_server_id_or_raise_and_get_community_user(
            ctx
        )

        self._permission_service.ensure_community_rank(
            community_user.community_rank, ctx.user.meta_rank, CommunityRank.OWNER
        )

        self._repo.delete(community.id)

        return DeletedCommunityDTO(community.name, community.limits)


@dataclass(frozen=True, slots=True, eq=False)
class CommunityQueryService:
    _repo: CommunityRepository
    _community_user_service: CommunityUserService
    _list_service: List

    def get_by_server_id_or_raise(self, ctx: InteractingUserContext) -> CommunityEntity:
        obj = self._repo.get_by_server_id(ctx.server_id)

        if obj is None:
            raise errors.NotInCommunity

        return obj

    def get_by_server_id_or_raise_and_get_community_user(
        self, ctx: InteractingUserContext
    ) -> tuple[CommunityEntity, CommunityUserEntity]:
        community = self.get_by_server_id_or_raise(ctx)
        community_user = self._community_user_service.get_or_create(
            CreateCommunityUserDTO(ctx.user, community.id)
        )

        return community, community_user

    def info(
        self,
        ctx: InteractingUserContext,
    ):
        community = self.get_by_server_id_or_raise(ctx)

        lists = self._list_repo.get_all(community.id)
        community_users = self._comm