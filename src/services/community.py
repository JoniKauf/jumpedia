from dataclasses import dataclass
from domain import errors
from domain.entities.community import CommunityEntity
from domain.entities.user import CommunityUserEntity, UserEntity
from domain.enums.rank import CommunityRank, MetaRank, ServerRank
from domain.types.id import ID
from domain.value_objects.community import CommunityName
from domain.value_objects.string import StrStore
from repositories.list import ListRepository
from repositories.server import ServerRepository
from repositories.task import TaskRepository
from repositories.user import CommunityUserRepository
from services.contexts.interacting_user import InteractingUserContext
from repositories.community import CommunityRepository
from repositories.dtos.community import CreateCommunityDTO
from repositories.dtos.user import CreateCommunityUserDTO
from domain.value_objects.limits import Limits
from services.permission import PermissionService
from services.dtos.community import CommunityInfoDTO, DeletedCommunityDTO
from services.list import ListService
from services.user import CommunityUserService


@dataclass(frozen=True, slots=True, eq=False)
class CommunityService:
    _ctx: InteractingUserContext
    _repo: CommunityRepository
    _access_service: CommunityAccessService
    _permission_service: PermissionService
    _community_user_service: CommunityUserService
    _list_service: ListService
    _server_repo: ServerRepository

    # -------------------------
    # CREATE COMMUNITY
    # -------------------------
    def create(
        self,
        name: CommunityName,
        owner_id: ID,
        owner_name: StrStore,
        limits: Limits,
    ) -> CommunityEntity:
        self._permission_service.ensure_meta_rank(MetaRank.ADMINISTRATOR)

        existing = self._repo.get_by_name(name)

        if existing is not None:
            raise errors.NameAlreadyTaken(name, existing)

        existing = self._repo.get_by_server_id(self._ctx.server_id)

        if existing is not None:
            raise errors.ServerAlreadyConnectedToACommunity(
                self._ctx.server_id, existing
            )

        del existing

        community = self._repo.create(CreateCommunityDTO(name, limits))

        self._server_repo.link(community, self._ctx.server_id)

        self._community_user_service.get_or_create(
            CreateCommunityUserDTO(
                UserEntity(owner_id, owner_name),
                community.id,
                CommunityRank.OWNER,
                None,
            ),
            overwrite_rank=True,
            overwrite_selected_list=True,
        )

        # TODO set as default
        self._list_service.create(StrStore("Main"))

        return community

    # -------------------------
    # DELETE COMMUNITY
    # -------------------------
    def delete(self) -> DeletedCommunityDTO:
        community, community_user = (
            self._access_service.get_by_server_id_or_raise_and_get_or_create_community_user()
        )

        self._permission_service.ensure_community_rank(
            community_user.community_rank, CommunityRank.OWNER
        )

        self._repo.delete(community.id)

        return DeletedCommunityDTO(community.name, community.limits)

    def link(self, community_name: CommunityName) -> CommunityEntity:
        self._permission_service.ensure_server_rank(ServerRank.ADMINISTRATOR)

        community = self._repo.get_by_server_id(self._ctx.server_id)

        if community is not None:
            raise errors.InCommunity(community)

        community = self._repo.get_by_name(community_name)

        if community is None:
            raise errors.NotFound(CommunityEntity)

        self._server_repo.link(community, self._ctx.server_id)

        return community

    def unlink(self) -> CommunityEntity:
        self._permission_service.ensure_server_rank(ServerRank.ADMINISTRATOR)

        community = self._access_service.get_by_server_id_or_raise()

        self._server_repo.unlink(self._ctx.server_id)

        return community


@dataclass(frozen=True, slots=True, eq=False)
class CommunityQueryService:
    _ctx: InteractingUserContext
    _repo: CommunityRepository
    _access_service: CommunityAccessService
    _community_user_repo: CommunityUserRepository
    _list_repo: ListRepository
    _task_repo: TaskRepository

    def info(self, community_name: CommunityName | None) -> CommunityInfoDTO:
        community = self._access_service.get_by_name_or_current(community_name)

        community_users = self._community_user_repo.get_all_by_community_id(
            community.id
        )
        lists = self._list_repo.get_all_by_community(community.id)
        task_count = self._task_repo.count_by_community(community.id)

        return CommunityInfoDTO(
            community.name,
            community.limits,
            community.default_selected_list_id,
            tuple(community_users),
            tuple(lists),
            task_count,
        )


@dataclass
class CommunityAccessService:
    _ctx: InteractingUserContext
    _repo: CommunityRepository
    _community_user_service: CommunityUserService

    def get_by_server_id_or_raise(self) -> CommunityEntity:
        obj = self._repo.get_by_server_id(self._ctx.server_id)

        if obj is None:
            raise errors.NotInCommunity()

        return obj

    def get_by_server_id_or_raise_and_get_or_create_community_user(
        self,
    ) -> tuple[CommunityEntity, CommunityUserEntity]:
        community = self.get_by_server_id_or_raise()
        community_user = self._community_user_service.get_or_create(
            CreateCommunityUserDTO(self._ctx.user, community.id)
        )

        return community, community_user

    def get_by_name_or_current(
        self, name: CommunityName | None = None
    ) -> CommunityEntity:
        if name is None:
            return self.get_by_server_id_or_raise()

        community = self._repo.get_by_name(name)

        if community is None:
            raise errors.NotFound(CommunityEntity)

        return community
