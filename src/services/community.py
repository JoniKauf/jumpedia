import typing as t
from dataclasses import dataclass

from domain.entities.community import CommunityEntity
from domain.entities.list import ListEntity
from domain.entities.member import MemberEntity
from domain.entities.user import UserEntity
from domain.enums.rank import CommunityRank, MetaRank
from domain.errors import business
from domain.sentinels.default import DEFAULT
from domain.value_objects.community import CommunityLimits, CommunityNameStr
from domain.value_objects.list import ListNameStr

lazy from repositories.community import CommunityRepository
from repositories.dtos.community import CommunityInsert
from repositories.dtos.member import MemberInsert

lazy from repositories.list import ListRepository
lazy from repositories.member import MemberRepository
lazy from repositories.server import ServerRepository
lazy from repositories.task import TaskRepository
lazy from services.contexts.interacting_user import InteractingUserContext
from services.dtos.community import (
    CommunityInfo,
    CommunitySummary,
    PreparedDeleteCommunity,
)
from services.dtos.user import UserRef

lazy from services.internal.permission import PermissionService
lazy from services.list import ListAccessService, ListService
lazy from services.member import MemberAccessService, MemberExistenceService


@dataclass(frozen=True, slots=True, eq=False)
class CommunityService:
    _ctx: InteractingUserContext

    _community_repository: CommunityRepository
    _server_repository: ServerRepository

    _list_access_service: ListAccessService
    _list_service: ListService
    _member_access_service: MemberAccessService
    _member_existence_service: MemberExistenceService
    _permission_service: PermissionService

    def create(
        self,
        name: CommunityNameStr,
        owner: UserRef,
        limits: CommunityLimits,
    ) -> CommunityEntity:
        self._permission_service.ensure_meta_rank(MetaRank.ADMINISTRATOR, None)

        existing = self._community_repository.get_by_name(name)

        if existing is not None:
            raise business.SynAlreadyTaken(existing, name, False, False)

        existing = self._community_repository.get_by_server_id(self._ctx.server_id)

        if existing is not None:
            raise business.ServerAlreadyConnectedToACommunity(
                self._ctx.server_id, existing
            )

        del existing

        community = self._community_repository.create(CommunityInsert(name, limits))

        self._server_repository.link(community, self._ctx.server_id)

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

        self._community_repository.update_default_selected_list_id(
            community.community_id, default_selected_list_id
        )

        return community

    def delete(self, prepared: PreparedDeleteCommunity) -> None:
        self._community_repository.delete(prepared.community_id)

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

        self._community_repository.update_default_selected_list_id(
            community.community_id, None if lst is None else lst.list_id
        )

        return community, lst


@dataclass(frozen=True, slots=True, eq=False)
class CommunityPrepareService:
    _member_access_service: MemberAccessService
    _permission_service: PermissionService

    def delete(self) -> tuple[PreparedDeleteCommunity, CommunityEntity]:
        community, member = self._member_access_service.get_convenient(DEFAULT)

        self._permission_service.ensure_community_rank(member, CommunityRank.OWNER)

        return PreparedDeleteCommunity(community.community_id), community


@dataclass(frozen=True, slots=True, eq=False)
class CommunityQueryService:
    _community_repository: CommunityRepository
    _list_repository: ListRepository
    _member_repository: MemberRepository
    _task_repository: TaskRepository

    _community_access_service: CommunityAccessService

    def get_info(self, community_name: CommunityNameStr | DEFAULT) -> CommunityInfo:
        community = self._community_access_service.get_convenient(community_name)

        members = self._member_repository.get_all_by_community_id(
            community.community_id
        )
        lists = self._list_repository.get_all_by_community(community.community_id)
        task_count = self._task_repository.count_by_community(community.community_id)

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
            for community in self._community_repository.get_all()
        }

        member_count = self._member_repository.count_grouped_by_community_id()
        list_counts = self._list_repository.count_grouped_by_community_id()
        task_counts = self._task_repository.count_grouped_by_community_id()

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

    _community_repository: CommunityRepository

    def get_by_name_or_raise(self, name: CommunityNameStr) -> CommunityEntity:
        community = self._community_repository.get_by_name(name)

        if community is None:
            raise business.NotFoundByName(CommunityEntity, name)

        return community

    def get_current_or_raise(self) -> CommunityEntity:
        community = self._community_repository.get_by_server_id(self._ctx.server_id)

        if community is None:
            raise business.NotInCommunity()

        return community

    def get_convenient(self, name: CommunityNameStr | DEFAULT) -> CommunityEntity:
        return (
            self.get_current_or_raise()
            if name is DEFAULT
            else self.get_by_name_or_raise(name)
        )
