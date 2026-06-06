from dataclasses import dataclass


from domain.entities.community import CommunityEntity
from domain.entities.list import ListEntity
from domain.entities.user import CommunityUserEntity
from domain.enums.rank import CommunityRank
from domain.types.id import ID
from domain.value_objects.list import ListName
from services.contexts.interacting_user import InteractingUserContext
from repositories.dtos.list import CreateListDTO
from repositories.list import ListRepository
from domain import errors
from services.permission import PermissionService
from services.community import (
    CommunityAccessService,
)
from services.dtos.list import ListInfoDTO
from services.user import CommunityUserAccessService

@dataclass(frozen=True, slots=True, eq=False)
class ListService:
    _ctx: InteractingUserContext
    _repo: ListRepository
    _permission_service: PermissionService
    _community_user_access_service: CommunityUserAccessService
    _community_access_service: CommunityAccessService

    def create(self, name: ListName) -> ListEntity:
        community = (
            self._community_access_service.get_by_name_or_current_or_raise()
        )
        community_user = self._community_user_access_service.get_or_create_current_with_defaults(community)

        self._permission_service.ensure_community_rank(
            community_user, CommunityRank.ADMINISTRATOR
        )

        list_count = self._repo.count_by_community(community.id)

        if list_count >= community.limits.community_list_count_max:
            raise errors.CountLimitReached(
                community.limits.community_list_count_max, ListEntity
            )

        if existing := self._repo.get_by_community_and_name(community.id, name):
            raise errors.NameAlreadyTaken(name, existing)

        return self._repo.create(CreateListDTO(community.id, name))

    def delete(self, community_id: ID, list_id: ID):
        lst = self._repo.get_by_id(list_id)

        if not lst or lst._community_id != community_id:
            raise errors.NotFound(ListEntity)

        self._repo.delete(list_id)

    def rename(self, old_name: ListName, new_name: ListName):
        community = self._community_access_service.get_by_name_or_current_or_raise()
        community_user = self._community_user_access_service.get_or_create_current_with_defaults(community)

        self._permission_service.ensure_community_rank(community_user, CommunityRank.ADMINISTRATOR)

        lst = self._repo.get_by_community_and_name(community.id, old_name)

        if lst is None:
            raise errors.NotFound(ListEntity)

        existing = self._repo.get_by_community_and_name(lst.community_id, lst.name)

        if existing is not None:
            raise errors.NameAlreadyTaken(lst.name, existing)

        lst.name = new_name

        self._repo.update(lst)


@dataclass(frozen=True, slots=True, eq=False)
class ListQueryService:
    _ctx: InteractingUserContext
    _repo: ListRepository
    _community_access_service: CommunityAccessService
    
    def info(self, name: ListName) -> ListInfoDTO:
        community = self._community_access_service.get_by_name_or_current_or_raise()

        lst = self._repo.get_by_community_and_name(community.id, name)

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


@dataclass(frozen=True, slots=True, eq=False)
class ListAccessService:
    _ctx: InteractingUserContext
    _repo: ListRepository
    _community_user_access_service: CommunityUserAccessService
    _community_access_service: CommunityAccessService

    def get_by_name(self, community: CommunityEntity, name: ListName) -> ListEntity:
        lst = self._repo.get_by_community_and_name(community.id, name)

        if lst is None:
            raise errors.NotFound(ListEntity)
        
        return lst
    
    def get_selected(self, community: CommunityEntity, community_user: CommunityUserEntity) -> ListEntity:
        selected_list_id = community_user.selected_list_id or community.default_selected_list_id

        if selected_list_id is None:
            raise errors.NoDefaultSelectedList()
        
        lst = self._repo.get_by_id(selected_list_id)

        assert lst is not None

        return lst