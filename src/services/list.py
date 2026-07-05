from dataclasses import dataclass

from domain import errors
from domain.entities.community import CommunityEntity
from domain.entities.list import ListEntity
from domain.entities.member import MemberEntity
from domain.enums.attribute import AttributeKind, AttributeSlotType, AttributeType
from domain.enums.rank import CommunityRank
from domain.types.common import ID
from domain.value_objects.attribute import AttributeSlot, AttributeSynStr
from domain.value_objects.community import CommunityNameStr
from domain.value_objects.list import ListNameStr
from domain.value_objects.position import Position
from repositories.attribute import AttributeRepository
from repositories.dtos.attribute import AttributeInsert
from repositories.dtos.list import ListInsert
from repositories.list import ListRepository
from repositories.task import TaskRepository
from services.community import CommunityAccessService
from services.contexts.interacting_user import InteractingUserContext
from services.dtos.list import DeletedList, ListInfo, ListSummary
from services.member import MemberAccessService
from services.permission import PermissionService


@dataclass(frozen=True, slots=True, eq=False)
class ListService:
    _list_repo: ListRepository
    _attribute_repo: AttributeRepository
    _permission_service: PermissionService
    _member_access_service: MemberAccessService
    _list_access_service: ListAccessService

    def create(self, name: ListNameStr) -> ListEntity:
        community, member = self._member_access_service.get_convenient(None)

        self._permission_service.ensure_community_rank(
            member, CommunityRank.ADMINISTRATOR
        )

        list_count = self._list_repo.count_by_community(community.community_id)

        if list_count >= community.limits.community_list_count_max:
            raise errors.CountLimitReached(
                community.limits.community_list_count_max, ListEntity
            )

        if existing := self._list_repo.get_by_community_and_name(
            community.community_id, name
        ):
            raise errors.SynAlreadyTaken(existing, name, False, False)

        lst = self._list_repo.create(ListInsert(community.community_id, name))

        # Create static attributes
        for i, kind in enumerate(AttributeKind):
            if kind is AttributeKind.NONE:
                continue

            self._attribute_repo.create(
                AttributeInsert(
                    list_id=lst.list_id,
                    name=AttributeSynStr(("ID", "Name", "Alias")[i]),
                    type=AttributeType.STATIC,
                    kind=kind,
                    slot=AttributeSlot(
                        type=(
                            AttributeSlotType.INTEGER,
                            AttributeSlotType.STRING,
                            AttributeSlotType.STRING,
                        )[i],
                        min_count=(1, 1, 0)[i],
                        max_count=(
                            1,
                            1,
                            community.limits.field_slot_count_max,
                        )[i],
                    ),
                    position=Position(i + 1),
                )
            )

        return lst

    def delete(self, name: ListNameStr) -> DeletedList:
        community, member, lst = self._list_access_service.get_convenient(None, name)

        self._permission_service.ensure_community_rank(
            member, CommunityRank.ADMINISTRATOR
        )

        self._list_repo.delete(lst.list_id)

        return DeletedList(community, lst.name)

    def rename(self, name_before: ListNameStr, name_after: ListNameStr) -> ListEntity:
        _, member, lst = self._list_access_service.get_convenient(None, name_before)

        self._permission_service.ensure_community_rank(
            member, CommunityRank.ADMINISTRATOR
        )

        name_taken_lst = self._list_repo.get_by_community_and_name(
            lst.community_id, name_after
        )

        if name_taken_lst is not None:
            raise errors.SynAlreadyTaken(name_taken_lst, lst.name, False, False)

        lst.name = name_after

        self._list_repo.update(lst)

        return lst


@dataclass(frozen=True, slots=True, eq=False)
class ListQueryService:
    _list_repo: ListRepository
    _attribute_repo: AttributeRepository
    _task_repo: TaskRepository
    _community_access_service: CommunityAccessService
    _list_access_service: ListAccessService

    def get_info(self, name: ListNameStr) -> ListInfo:
        community, _, lst = self._list_access_service.get_convenient(None, name)

        attributes = self._attribute_repo.get_all_by_list_id(
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
        community = self._community_access_service.get_convenient(None)

        lists = self._list_repo.get_all_by_community(community.community_id)

        attributes_by_list = self._attribute_repo.get_grouped_by_list_id(
            community.community_id
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
            raise errors.NotFoundByName(name, ListEntity)

        return lst

    def get_by_priority(
        self, community: CommunityEntity, member: MemberEntity
    ) -> ListEntity:
        """Get the selected list in priority order:

        1. The user's selected list if specified
        2. otherwise the community's default selected list
        3. otherwise raise
        """

        selected_list_id = member.selected_list_id or community.default_selected_list_id

        if selected_list_id is None:
            raise errors.NoDefaultSelectedList()

        lst = self._list_repo.get_by_id(selected_list_id)

        assert lst is not None

        return lst

    def get_convenient(
        self, community_name: CommunityNameStr | None, list_name: ListNameStr | None
    ) -> tuple[CommunityEntity, MemberEntity, ListEntity]:
        community, member = self._member_access_service.get_convenient(community_name)

        lst: ListEntity

        if list_name is None:
            lst = self.get_by_priority(community, member)
        else:
            lst = self.get_by_community_and_name_or_raise(community, list_name)

        return (community, member, lst)
