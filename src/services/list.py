from dataclasses import dataclass


from domain.entities.community import CommunityEntity
from domain.entities.list import ListEntity
from domain.entities.user import CommunityUserEntity
from domain.enums.rank import CommunityRank
from domain.types.id import ID
from domain.value_objects.community import CommunityName
from domain.value_objects.list import ListName
from repositories.attribute import AttributeRepository
from repositories.task import TaskRepository
from services.contexts.interacting_user import InteractingUserContext
from repositories.dtos.list import CreateListDTO
from repositories.list import ListRepository
from domain import errors
from services.permission import PermissionService
from services.community import (
    CommunityAccessService,
)
from services.dtos.list import DeletedListDTO, ListInfoDTO, ListSummaryDTO
from services.user import CommunityUserAccessService

@dataclass(frozen=True, slots=True, eq=False)
class ListService:
    _ctx: InteractingUserContext
    _repo: ListRepository
    _access_service: ListAccessService
    _permission_service: PermissionService
    _community_user_access_service: CommunityUserAccessService

    def create(self, name: ListName) -> ListEntity:
        community, community_user = (
            self._community_user_access_service.get_convenient(None)
        )

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
        
        # TODO create static attributes

        return self._repo.create(CreateListDTO(community.id, name))

    def delete(self, name: ListName) -> DeletedListDTO:
        _, community_user, lst = self._access_service.get_convenient(None, name)

        self._permission_service.ensure_community_rank(community_user, CommunityRank.ADMINISTRATOR)

        self._repo.delete(lst.id)

        return DeletedListDTO(lst.community_id, lst.name)


    def rename(self, name_before: ListName, name_after: ListName) -> ListEntity:
        _, community_user, lst = self._access_service.get_convenient(None, name_before)

        self._permission_service.ensure_community_rank(community_user, CommunityRank.ADMINISTRATOR)

        name_taken_lst = self._repo.get_by_community_and_name(lst.community_id, name_after)

        if name_taken_lst is not None:
            raise errors.NameAlreadyTaken(lst.name, name_taken_lst)

        lst.name = name_after

        self._repo.update(lst)

        return lst


@dataclass(frozen=True, slots=True, eq=False)
class ListQueryService:
    _ctx: InteractingUserContext
    _repo: ListRepository
    _access_service: ListAccessService
    _community_access_service: CommunityAccessService
    _attribute_repo: AttributeRepository
    _task_repo: TaskRepository
    
    def info(self, name: ListName) -> ListInfoDTO:
        community, _, lst = self._access_service.get_convenient(None, name)

        attributes = self._attribute_repo.get_all_by_list_id(lst.id)
        task_count = self._task_repo.count_by_list(lst.id)
        is_default = (
            community.default_selected_list_id == lst.id
        )

        return ListInfoDTO(
            name=lst.name,
            attributes=tuple(attributes),
            task_count=task_count,
            is_default_selected_list=is_default,
        )
    
    def summaries(self) -> tuple[ListSummaryDTO, ...]:
        community = self._community_access_service.get_convenient(None)

        lists = self._repo.get_all_by_community(community.id)

        attributes_by_list = (
            self._attribute_repo.get_grouped_by_list_id(
                community.id
            )
        )

        task_counts = (
            self._task_repo.count_grouped_by_list_id(
                community.id,
            )
        )

        default_list_id = community.default_selected_list_id

        return tuple(
            ListSummaryDTO(
                name=lst.name,
                attributes=tuple(attributes_by_list.get(lst.id, ())),
                task_count=task_counts.get(lst.id, 0),
                is_default_selected_list=(lst.id == default_list_id),
            )
            for lst in lists
        )


@dataclass(frozen=True, slots=True, eq=False)
class ListAccessService:
    _ctx: InteractingUserContext
    _repo: ListRepository
    _community_user_access_service: CommunityUserAccessService

    def get_by_community_and_name_or_raise(self, community: CommunityEntity, name: ListName) -> ListEntity:
        lst = self._repo.get_by_community_and_name(community.id, name)

        if lst is None:
            raise errors.NotFoundByName(name, ListEntity)
        
        return lst
    
    def get_by_priority(self, community: CommunityEntity, community_user: CommunityUserEntity) -> ListEntity:
        """Get the selected list in priority order:

        1. The user's selected list if specified
        2. otherwise the community's default selected list
        3. otherwise raise
        """

        selected_list_id = community_user.selected_list_id or community.default_selected_list_id

        if selected_list_id is None:
            raise errors.NoDefaultSelectedList()
        
        lst = self._repo.get_by_id(selected_list_id)

        assert lst is not None

        return lst
    
    def get_convenient(self, community_name: CommunityName | None, list_name: ListName | None) -> tuple[CommunityEntity, CommunityUserEntity, ListEntity]:
        community, community_user = self._community_user_access_service.get_convenient(community_name)

        lst: ListEntity

        if list_name is None:
            lst = self.get_by_priority(community, community_user)
        else:
            lst = self.get_by_community_and_name_or_raise(community, list_name)

        return (community, community_user, lst)