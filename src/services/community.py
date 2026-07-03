from dataclasses import dataclass

from domain import errors
from domain.entities.community import CommunityEntity
from domain.entities.list import ListEntity
from domain.entities.user import UserEntity
from domain.enums.rank import CommunityRank, MetaRank
from domain.types.user import UserID
from domain.value_objects.community import CommunityLimits, CommunityNameStr
from domain.value_objects.list import ListNameStr
from domain.value_objects.user import UserNameStr
from repositories.community import CommunityRepository
from repositories.community_user import CommunityUserRepository
from repositories.dtos.community import CommunityInsert
from repositories.dtos.community_user import CommunityUserInsert
from repositories.list import ListRepository
from repositories.server import ServerRepository
from repositories.task import TaskRepository
from services.community_user import CommunityUserAccessService, CommunityUserService
from services.contexts.interacting_user import InteractingUserContext
from services.dtos.community import CommunityInfo, CommunitySummary, DeletedCommunity
from services.dtos.task import UserRef
from services.list import ListService
from services.permission import PermissionService


@dataclass(frozen=True, slots=True, eq=False)
class CommunityService:
    _ctx: InteractingUserContext
    _server_repo: ServerRepository
    _community_repo: CommunityRepository
    _permission_service: PermissionService
    _community_access_service: CommunityAccessService
    _community_user_access_service: CommunityUserAccessService
    _community_user_service: CommunityUserService
    _list_service: ListService

    def create(
        self,
        name: CommunityNameStr,
        owner: UserRef,
        limits: CommunityLimits,
    ) -> CommunityEntity:
        self._permission_service.ensure_meta_rank(MetaRank.ADMINISTRATOR)

        existing = self._community_repo.get_by_name(name)

        if existing is not None:
            raise errors.NameAlreadyTaken(name, existing)

        existing = self._community_repo.get_by_server_id(self._ctx.server_id)

        if existing is not None:
            raise errors.ServerAlreadyConnectedToACommunity(
                self._ctx.server_id, existing
            )

        del existing

        community = self._community_repo.create(CommunityInsert(name, limits))

        self._server_repo.link(community, self._ctx.server_id)

        self._community_user_service.get_or_create(
            CommunityUserInsert(
                UserEntity(owner.id, owner.name),
                community.community_id,
                CommunityRank.OWNER,
                None,
            ),
            overwrite_rank=True,
            overwrite_selected_list=True,
        )

        community.default_selected_list_id = self._list_service.create(
            ListNameStr("Main")
        ).list_id

        self._community_repo.update(community)

        return community

    def delete(self) -> DeletedCommunity:
        community, community_user = self._community_user_access_service.get_convenient(
            None
        )

        self._permission_service.ensure_community_rank(
            community_user, CommunityRank.OWNER
        )

        self._community_repo.delete(community.community_id)

        return DeletedCommunity(community.name, community.created, community.limits)


@dataclass(frozen=True, slots=True, eq=False)
class CommunityQueryService:
    _community_repo: CommunityRepository
    _list_repo: ListRepository
    _task_repo: TaskRepository
    _community_user_repo: CommunityUserRepository
    _community_access_service: CommunityAccessService

    def get_info(self, community_name: CommunityNameStr | None) -> CommunityInfo:
        community = self._community_access_service.get_convenient(community_name)

        community_users = self._community_user_repo.get_all_by_community_id(
            community.community_id
        )
        lists = self._list_repo.get_all_by_community(community.community_id)
        task_count = self._task_repo.count_by_community(community.community_id)

        default_selected_list: ListEntity | None = None

        if community.default_selected_list_id is not None:
            for lst in lists:
                if lst.list_id == community.default_selected_list_id:
                    default_selected_list = lst
                    break

        return CommunityInfo(
            community.name,
            default_selected_list,
            community.created,
            community.limits,
            tuple(community_users),
            tuple(lists),
            task_count,
        )

    def get_summaries(self) -> tuple[CommunitySummary, ...]:
        id_to_community = {
            community.community_id: community
            for community in self._community_repo.get_all()
        }

        community_user_count = self._community_user_repo.count_grouped_by_community_id()
        list_counts = self._list_repo.count_grouped_by_community_id()
        task_counts = self._task_repo.count_grouped_by_community_id()

        return tuple(
            CommunitySummary(
                community.name,
                community.created,
                community_user_count.get(id, 0),
                list_counts.get(id, 0),
                task_counts.get(id, 0),
            )
            for id, community in id_to_community.items()
        )


@dataclass(frozen=True, slots=True, eq=False)
class CommunityAccessService:
    _ctx: InteractingUserContext
    _community_repo: CommunityRepository

    def get_by_name_or_raise(self, name: CommunityNameStr) -> CommunityEntity:
        community = self._community_repo.get_by_name(name)

        if community is None:
            raise errors.NotFoundByName(name, CommunityEntity)

        return community

    def get_current_or_raise(self) -> CommunityEntity:
        community = self._community_repo.get_by_server_id(self._ctx.server_id)

        if community is None:
            raise errors.NotInCommunity()

        return community

    def get_convenient(self, name: CommunityNameStr | None) -> CommunityEntity:
        return (
            self.get_current_or_raise()
            if name is None
            else self.get_by_name_or_raise(name)
        )
