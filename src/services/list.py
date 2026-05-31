from dataclasses import dataclass

from discord import Interaction

from db.models import List
from domain.entities.list import ListEntity
from domain.enums.rank import CommunityRank
from domain.types.id import ID
from domain.value_objects.limits import Limits
from domain.value_objects.string import StrStore
from interfaces.contexts.command import CommandContext
from services.contexts.interacting_user import InteractingUserContext
from repositories.attribute import AttributeRepository
from repositories.community import CommunityRepository
from repositories.dtos.list import CreateListDTO
from repositories.list import ListRepository
from sqlalchemy.orm import Session
from domain import errors
from services.permission import PermissionService
from services.community import CommunityAccessService, CommunityQueryService, CommunityService
from services.dtos.list import ListInfoDTO


@dataclass(frozen=True, slots=True, eq=False)
class ListService:
    _ctx: InteractingUserContext
    _repo: ListRepository
    _permission_service: PermissionService
    _community_access_service: CommunityAccessService

    # -------------------------
    # CREATE LIST
    # -------------------------
    def create(self, name: StrStore) -> ListEntity:
        community, community_user = self._community_access_service.get_by_server_id_or_raise_and_get_or_create_community_user()

        self._permission_service.ensure_community_rank(community_user.community_rank, CommunityRank.ADMINISTRATOR)

        # TODO somehow replace this part with entity so invariants are checked internal
        if len(name) > Limits.LIST_NAME_LENGTH_MAX:
            raise errors.NameTooLong(name, Limits.LIST_NAME_LENGTH_MAX, ListEntity)
        
        list_count = self._repo.count(community.id)

        if list_count >= community.limits.community_list_count_max:
            raise errors.CountLimitReached(community.limits.community_list_count_max, ListEntity)

        if existing := self._repo.get_by_name(community.id, name):
            raise errors.NameAlreadyTaken(name, existing)

        return self._repo.create(CreateListDTO(community.id, name))

    # -------------------------
    # DELETE LIST
    # -------------------------
    def delete(self, community_id: ID, list_id: ID):
        lst = self._repo.get_by_id(list_id)

        if not lst or lst._community_id != community_id:
            raise errors.NotFound(ListEntity)

        self._repo.delete(list_id)

    # -------------------------
    # RENAME LIST
    # -------------------------
    def rename(self, list_id: int, name: StrStore):
        lst = self._repo.get_by_id(list_id)

        if lst is None:
            raise errors.NotFound(ListEntity)

        if self._repo.get_by_name(lst._community_id, lst.name):
            raise ValueError("name already taken")

        lst.name = name


@dataclass(frozen=True, slots=True, eq=False)
class ListQueryService:
    def info(self, name: StrStore) -> ListInfoDTO:
        community = self._community_query_service.get_by_server_id_or_raise()

        lst = self._repo.get_by_name(community.id, name)

        if lst is None:
            raise errors.NotFound(ListEntity)

        attributes = self._attribute_repo.get_by_list_id(lst.id)
        task_count = self._repo.count_tasks(lst.id)
        is_default = (
            self._community_repo.get_default_selected_list(lst._community_id) == lst.id
        )

        return ListInfoDTO(
            name=lst.name,
            attributes=tuple(attributes),
            task_count=task_count,
            is_default_selected_list=is_default,
        )
