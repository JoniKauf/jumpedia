from dataclasses import dataclass

from domain.entities.community import CommunityEntity
from domain.entities.list import ListEntity
from domain.entities.member import MemberEntity
from domain.enums.attribute import AttributeKind, AttributeSlotType, AttributeType
from domain.enums.rank import CommunityRank
from domain.errors import business
from domain.sentinels.default import DEFAULT
from domain.value_objects.attribute import AttributeFieldConfig, AttributeSynStr, KindedAttributeDefaultProperties
from domain.value_objects.community import CommunityNameStr
from domain.value_objects.list import ListNameStr
from domain.value_objects.position import Position
from repositories.attribute import AttributeRepository
from repositories.dtos.attribute import AttributeInsert
from repositories.dtos.list import ListInsert
from repositories.list import ListRepository
from repositories.task import TaskRepository
from services.community import CommunityAccessService
from services.dtos.list import ListInfo, ListSummary, PreparedDeleteList
from services.internal.permission import PermissionService
from services.member import MemberAccessService


@dataclass(frozen=True, slots=True, eq=False)
class ListService:
    _list_repo: ListRepository
    _attribute_repo: AttributeRepository
    _permission_service: PermissionService
    _member_access_service: MemberAccessService
    _list_access_service: ListAccessService

    def create(self, name: ListNameStr) -> ListEntity:
        community, member = self._member_access_service.get_convenient(DEFAULT)

        self._permission_service.ensure_community_rank(
            member, CommunityRank.ADMINISTRATOR
        )

        list_count = self._list_repo.count_by_community(community.community_id)

        if list_count >= community.limits.community_list_count_max:
            raise business.CountLimitReached(
                community.limits.community_list_count_max, ListEntity
            )

        if existing := self._list_repo.get_by_community_and_name(
            community.community_id, name
        ):
            raise business.SynAlreadyTaken(existing, name, False, False)

        lst = self._list_repo.create(ListInsert(community.community_id, name))

        # Create kinded attributes
        for attr in KindedAttributeDefaultProperties.DEFAULTS:
            self._attribute_repo.create(
                AttributeInsert(
                    lst.list_id,
                    attr.name,
                    attr.kind.type,
                    attr.kind,
                    attr.field_config,
                    attr.position
                )
            )

        return lst

    def delete(self, prepared: PreparedDeleteList) -> None:
        self._list_repo.delete(prepared.list_id)

    def edit_name(
        self, current_name: ListNameStr, new_name: ListNameStr
    ) -> ListNameStr:
        _, member, lst = self._list_access_service.get_convenient(DEFAULT, current_name)

        self._permission_service.ensure_community_rank(
            member, CommunityRank.ADMINISTRATOR
        )

        name_taken_lst = self._list_repo.get_by_community_and_name(
            lst.community_id, new_name
        )

        if name_taken_lst is not None:
            raise business.SynAlreadyTaken(name_taken_lst, lst.name, False, False)

        self._list_repo.update(lst)

        return lst.name


@dataclass(frozen=True, slots=True, eq=False)
class ListPrepareService:
    _list_access_service: ListAccessService
    _permission_service: PermissionService

    def delete(
        self, name: ListNameStr
    ) -> tuple[PreparedDeleteList, CommunityEntity, ListEntity]:
        community, member, lst = self._list_access_service.get_convenient(DEFAULT, name)

        self._permission_service.ensure_community_rank(
            member, CommunityRank.ADMINISTRATOR
        )

        return PreparedDeleteList(lst.list_id), community, lst


@dataclass(frozen=True, slots=True, eq=False)
class ListQueryService:
    _list_repo: ListRepository
    _attribute_repo: AttributeRepository
    _task_repo: TaskRepository
    _community_access_service: CommunityAccessService
    _list_access_service: ListAccessService

    def get_info(self, name: ListNameStr) -> ListInfo:
        community, _, lst = self._list_access_service.get_convenient(DEFAULT, name)

        attributes = self._attribute_repo.get_all_by_list_id_ordered_by_position(
            lst.list_id, AttributeType.ALL()
        )
        task_count = self._task_repo.count_by_list(lst.list_id)
        is_default = community.default_selected_list_id == lst.list_id

        return ListInfo(
            name=lst.name,
            attributes=tuple(attributes),
            task_count=task_count,
            is_default_selected_list=is_default,
        )

    def get_summaries(self) -> tuple[ListSummary, ...]:
        community = self._community_access_service.get_convenient(DEFAULT)

        lists = self._list_repo.get_all_by_community(community.community_id)

        attributes_by_list = (
            self._attribute_repo.get_grouped_by_list_id_ordered_by_position(
                community.community_id
            )
        )

        task_counts = self._task_repo.count_grouped_by_list_id(
            community.community_id,
        )

        default_list_id = community.default_selected_list_id

        return tuple(
            ListSummary(
                name=lst.name,
                attributes=tuple(attributes_by_list.get(lst.list_id, ())),
                task_count=task_counts.get(lst.list_id, 0),
                is_default_selected_list=(lst.list_id == default_list_id),
            )
            for lst in lists
        )


@dataclass(frozen=True, slots=True, eq=False)
class ListAccessService:
    _list_repo: ListRepository
    _member_access_service: MemberAccessService

    def get_by_community_and_name_or_raise(
        self, community: CommunityEntity, name: ListNameStr
    ) -> ListEntity:
        lst = self._list_repo.get_by_community_and_name(community.community_id, name)

        if lst is None:
            raise business.NotFoundByName(name, ListEntity)

        return lst

    def get_by_priority(
        self, community: CommunityEntity, member: MemberEntity
    ) -> ListEntity:
        """Get the selected list in priority order:

        1. The user's selected list if specified
        2. otherwise the community's default selected list if specified
        3. otherwise raise
        """

        selected_list_id = member.selected_list_id or community.default_selected_list_id

        if selected_list_id is None:
            raise business.NoDefaultSelectedList()

        lst = self._list_repo.get_by_id(selected_list_id)

        assert lst is not None

        return lst

    def get_convenient(
        self,
        community_name: CommunityNameStr | DEFAULT,
        list_name: ListNameStr | DEFAULT,
    ) -> tuple[CommunityEntity, MemberEntity, ListEntity]:
        community, member = self._member_access_service.get_convenient(community_name)

        lst: ListEntity

        if list_name is DEFAULT:
            lst = self.get_by_priority(community, member)
        else:
            lst = self.get_by_community_and_name_or_raise(community, list_name)

        return (community, member, lst)
