import typing as t
from dataclasses import dataclass

from domain import errors
from domain.entities.community import CommunityEntity
from domain.entities.list import ListEntity
from domain.entities.member import MemberEntity
from domain.entities.user import UserEntity
from domain.enums.rank import CommunityRank, MetaRank
from domain.sentinels.default import DEFAULT
from domain.value_objects.community import CommunityLimits, CommunityNameStr
from domain.value_objects.list import ListNameStr
from repositories.community import CommunityRepository
from repositories.dtos.community import CommunityInsert
from repositories.dtos.member import MemberInsert
from repositories.list import ListRepository
from repositories.member import MemberRepository
from repositories.server import ServerRepository
from repositories.task import TaskRepository
from services.contexts.interacting_user import InteractingUserContext
from services.dtos.community import CommunityInfo, CommunitySummary, DeletedCommunity
from services.dtos.user import UserRef
from services.list import ListAccessService, ListService
from services.member import MemberAccessService, MemberExistenceService
from services.internal.permission import PermissionService


@dataclass(frozen=True, slots=True, eq=False)
class CommunityService:
    _ctx: InteractingUserContext
    _server_repo: ServerRepository
    _community_repo: CommunityRepository
    _permission_service: PermissionService
    _community_access_service: CommunityAccessService
    _member_access_service: MemberAccessService
    _member_existence_service: MemberExistenceService
    _list_access_service: ListAccessService
    _list_service: ListService

    def create(
        self,
        name: CommunityNameStr,
        owner: UserRef,
        limits: CommunityLimits,
    ) -> CommunityEntity:
        self._permission_service.ensure_meta_rank(MetaRank.ADMINISTRATOR, None)

        existing = self._community_repo.get_by_name(name)

        if existing is not None:
            raise errors.SynAlreadyTaken(existing, name, False, False)

        existing = self._community_repo.get_by_server_id(self._ctx.server_id)

        if existing is not None:
            raise errors.ServerAlreadyConnectedToACommunity(
                self._ctx.server_id, existing
            )

        del existing

        community = self._community_repo.create(CommunityInsert(name, limits))

        self._server_repo.link(community, self._ctx.server_id)

        self._member_existence_service.get_or_create(
            MemberInsert(
                UserEntity(owner.id, owner.name),
                community.community_id,
                CommunityRank.OWNER,
                None,
            ),
            overwrite_rank=True,
            overwrite_selected_list=True,
        )

        default_selected_list_id = self._list_service.create(
            ListNameStr("Main")
        ).list_id

        self._community_repo.update_default_selected_list_id(
            community.community_id, default_selected_list_id
        )

        return community

    def delete(self) -> DeletedCommunity:
        community, member = self._member_access_service.get_convenient(DEFAULT)

        self._permission_service.ensure_community_rank(member, CommunityRank.OWNER)

        self._community_repo.delete(community.community_id)

        return DeletedCommunity(community.name, community.created, community.limits)

    @t.overload
    def edit_default_selected_list(
        self, list_name: ListNameStr
    ) -> tuple[CommunityEntity, ListEntity]:
        pass

    @t.overload
    def edit_default_selected_list(
        self, list_name: None
    ) -> tuple[CommunityEntity, None]:
        pass

    def edit_default_selected_list(
        self, list_name: ListNameStr | None
    ) -> tuple[CommunityEntity, ListEntity | None]:
        community: CommunityEntity
        member: MemberEntity
        lst: ListEntity | None

        if list_name is None:
            community, member = self._member_access_service.get_convenient(DEFAULT)
            lst = None
        else:
            community, member, lst = self._list_access_service.get_convenient(
                DEFAULT, list_name
            )

        self._permission_service.ensure_community_rank(
            member, CommunityRank.ADMINISTRATOR
        )

        self._community_repo.update_default_selected_list_id(
            community.community_id, None if lst is None else lst.list_id
        )

        return community, lst


@dataclass(frozen=True, slots=True, eq=False)
class CommunityQueryService:
    _community_repo: CommunityRepository
    _list_repo: ListRepository
    _task_repo: TaskRepository
    _member_repo: MemberRepository
    _community_access_service: CommunityAccessService

    def get_info(self, community_name: CommunityNameStr | DEFAULT) -> CommunityInfo:
        community = self._community_access_service.get_convenient(community_name)

        members = self._member_repo.get_all_by_community_id(community.community_id)
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
            tuple(members),
            tuple(lists),
            task_count,
        )

    def get_summaries(self) -> tuple[CommunitySummary, ...]:
        id_to_community = {
            community.community_id: community
            for community in self._community_repo.get_all()
        }

        member_count = self._member_repo.count_grouped_by_community_id()
        list_counts = self._list_repo.count_grouped_by_community_id()
        task_counts = self._task_repo.count_grouped_by_community_id()

        return tuple(
            CommunitySummary(
                community.name,
                community.created,
                member_count.get(id, 0),
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

    def get_convenient(self, name: CommunityNameStr | DEFAULT) -> CommunityEntity:
        return (
            self.get_current_or_raise()
            if name is DEFAULT
            else self.get_by_name_or_raise(name)
        )
