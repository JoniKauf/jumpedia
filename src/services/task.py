import types as ts
import typing as t
from dataclasses import dataclass

from domain import errors
from domain.entities.community import CommunityEntity
from domain.entities.community_user import CommunityUserEntity
from domain.entities.list import ListEntity
from domain.entities.task import TaskEntity
from domain.enums.attribute import AttributeType
from domain.enums.rank import CommunityRank
from domain.value_objects.attribute import AttributeEntity, AttributeSynStr
from domain.value_objects.community import CommunityNameStr
from domain.value_objects.index import Index
from domain.value_objects.list import ListNameStr
from domain.value_objects.field_slot import FieldSlotStr
from repositories.attribute import AttributeRepository
from repositories.collection_entry import CollectionEntryRepository
from repositories.dtos.community_user import CommunityUserInsert
from repositories.dtos.task import TaskAliasInsert, TaskInsert
from repositories.dtos.user import UserInsert
from repositories.task import TaskRepository
from repositories.field_slot import (
    FieldSlotInsert,
    FieldSlotRepository,
)
from services.community_user import CommunityUserService
from services.field_mapping import FieldMappingService
from services.contexts.interacting_user import InteractingUserContext
from services.dtos.task import (
    DeletedTask,
    TaskInfo,
    TaskSummariesData,
    TaskSummary,
    UserRef,
)
from services.list import ListAccessService
from services.permission import PermissionService
from services.user import UserService


@dataclass(frozen=True, slots=True, eq=False)
class TaskService:
    _ctx: InteractingUserContext
    _task_repo: TaskRepository
    _attribute_repo: AttributeRepository
    _permission_service: PermissionService
    _list_access_service: ListAccessService
    _field_mapping_service: FieldMappingService
    _collection_entry_repo: CollectionEntryRepository
    _field_slot_repo: FieldSlotRepository
    _task_access_service: TaskAccessService
    _user_service: UserService
    _community_user_service: CommunityUserService

    def create(
        self,
        name: FieldSlotStr,
        list_name: ListNameStr,
        aliases: t.Sequence[FieldSlotStr],
        field_mapping: t.Mapping[AttributeSynStr, t.Sequence[FieldSlotStr]],
    ) -> TaskEntity:
        # --- Get Data --- #
        community, community_user, lst = self._list_access_service.get_convenient(
            None, list_name
        )

        # --- Verify Rank --- #
        self._permission_service.ensure_community_rank(
            community_user, CommunityRank.HELPER
        )

        # --- Verify Limit Of Count Not Exceeded --- #
        task_count = self._task_repo.count_by_list(lst.list_id)

        if task_count >= community.limits.list_task_count_max:
            raise errors.CountLimitReached(
                community.limits.list_task_count_max, TaskEntity
            )

        syns: tuple[FieldSlotStr, ...] = (name, *aliases)

        if len(aliases) > community.limits.field_slot_count_max:
            raise errors.AliasCountLimitReached(
                community.limits.field_slot_count_max, name
            )

        # --- Verify Syn Uniquness Across Each Other And Across All Tasks --- #
        FieldSlotStr.raise_if_not_norm_unique(syns)

        existing_same_syn = self._task_repo.get_by_list_id_and_any_syn(
            lst.list_id, syns
        )

        if existing_same_syn is not None:
            raise errors.SynAlreadyTaken(*existing_same_syn)

        # --- Validate And Create Task Attribute Value Mapping --- #

        ATTRIBUTE_TYPES: t.Final = AttributeType.TASK.as_set()

        syn_to_attr = self._attribute_repo.get_syn_to_attribute_by_list_id(
            lst.list_id, ATTRIBUTE_TYPES
        )
        attr_id_to_collection = (
            self._collection_entry_repo.get_grouped_collections_by_list_id(
                lst.list_id, ATTRIBUTE_TYPES
            )
        )

        avm = self._field_mapping_service.validate_and_build(
            field_mapping, syn_to_attr, attr_id_to_collection
        )

        # --- Create Task ---
        task_entity = self._task_repo.create(TaskInsert(lst.list_id, name))

        # --- Create Task Aliases ---
        self._task_repo.create_many_aliases(
            TaskAliasInsert(task_entity.task_id, Index(i), lst.list_id, alias)
            for i, alias in enumerate(aliases)
        )

        # --- Create Task Attribute Slots ---
        if avm:
            inserts: list[FieldSlotInsert] = []

            for attr, value in avm.items():
                for i, slot in enumerate(value):
                    inserts.append(
                        FieldSlotInsert(
                            task_entity.task_id, attr.attribute_id, Index(i), slot
                        )
                    )

            if inserts:
                _ = self._field_slot_repo.create_many(inserts)

        return task_entity

    def delete(self, name: FieldSlotStr, list_name: ListNameStr) -> DeletedTask:
        _, community_user, lst, task = self._task_access_service.get_convenient(
            None, list_name, name, True
        )

        self._permission_service.ensure_community_rank(
            community_user, CommunityRank.MODERATOR
        )

        self._task_repo.delete(task.task_id)

        return DeletedTask(task.name, lst)

    def give_to_user(
        self,
        syn: FieldSlotStr,
        list_name: ListNameStr | None,
        user_field_mapping: t.Mapping[AttributeSynStr, tuple[FieldSlotStr, ...]],
        user: UserRef | None,
    ):
        community, actor_community_user, lst, task = (
            self._task_access_service.get_convenient(None, list_name, syn, False)
        )

        community_user: CommunityUserEntity

        if user is None or user.id == actor_community_user.user.user_id:
            community_user = actor_community_user
        else:
            self._permission_service.ensure_community_user_can_act_for_others(actor_community_user)
            
            community_user = self._community_user_service.get_or_create(
                CommunityUserInsert(
                    self._user_service.get_or_create(UserInsert(user.id, user.name)),
                    community.community_id,
                )
            )

        del actor_community_user

        ATTRIBUTE_TYPES: t.Final = AttributeType.USER.as_set()

        syn_to_attr = self._attribute_repo.get_syn_to_attribute_by_list_id(
            lst.list_id, ATTRIBUTE_TYPES
        )
        attr_id_to_collection = (
            self._collection_entry_repo.get_grouped_collections_by_list_id(
                lst.list_id, ATTRIBUTE_TYPES
            )
        )

        self._field_mapping_service.validate_and_build(user_field_mapping, syn_to_attr, attr_id_to_collection)




@dataclass(frozen=True, slots=True, eq=False)
class TaskQueryService:
    _task_access_service: TaskAccessService
    _task_repo: TaskRepository
    _attribute_repo: AttributeRepository
    _field_slot_repo: FieldSlotRepository
    _list_access_service: ListAccessService

    def get_info(self, syn: FieldSlotStr, list_name: ListNameStr | None) -> TaskInfo:
        _, _, lst, task = self._task_access_service.get_convenient(
            None, list_name, syn, False
        )

        ATTRIBUTE_TYPES: t.Final = AttributeType.TASK.as_set()

        id_to_attr = self._attribute_repo.get_all_by_list_id(
            lst.list_id, ATTRIBUTE_TYPES
        )

        aliases = self._task_repo.get_aliases_by_task_id(task.task_id)
        field_mapping = self._field_slot_repo.get_field_mapping_by_task_id(
            task.task_id, ATTRIBUTE_TYPES
        )
        static_attributes = tuple(
            self._attribute_repo.get_all_by_list_id(
                lst.list_id, AttributeType.STATIC.as_set()
            )
        )

        assert len(static_attributes) == 3

        return TaskInfo(
            task.task_id,
            task.name,
            aliases,
            lst,
            ts.MappingProxyType(
                {
                    id_to_attr[k]: tuple(slot.slot for slot in v)
                    for k, v in field_mapping.items()
                }
            ),
            static_attributes,
        )

    def get_summaries(self, list_name: ListNameStr | None) -> TaskSummariesData:
        _, _, lst = self._list_access_service.get_convenient(None, list_name)

        ATTRIBUTE_TYPES: t.Final = AttributeType.TASK.as_set()
        attrs = self._attribute_repo.get_all_by_list_id(lst.list_id, ATTRIBUTE_TYPES)
        id_to_attr = {attr.attribute_id: attr for attr in attrs}

        tasks = self._task_repo.get_all_by_list_id(lst.list_id)
        task_id_to_aliases = self._task_repo.get_grouped_aliases_by_list_id(lst.list_id)
        task_id_to_field_mapping = self._field_slot_repo.get_field_mapping_by_list_id(
            lst.list_id, ATTRIBUTE_TYPES
        )
        static_attributes = tuple(
            self._attribute_repo.get_all_by_list_id(
                lst.list_id, AttributeType.STATIC.as_set()
            )
        )

        assert len(static_attributes) == 3

        return TaskSummariesData(
            tuple(
                TaskSummary(
                    task.task_id,
                    task.name,
                    task_id_to_aliases[task.task_id],
                    lst,
                    ts.MappingProxyType(
                        {
                            id_to_attr[k]: tuple(slot.slot for slot in v)
                            for k, v in task_id_to_field_mapping[task.task_id].items()
                        }
                    ),
                )
                for task in tasks
            ),
            static_attributes,
            attrs,
        )


@dataclass(frozen=True, slots=True, eq=False)
class TaskAccessService:
    _ctx: InteractingUserContext
    _task_repo: TaskRepository
    _list_access_service: ListAccessService

    def get_by_list_and_name_or_raise(
        self, lst: ListEntity, name: FieldSlotStr
    ) -> TaskEntity:
        task = self._task_repo.get_by_list_id_and_name(lst.list_id, name)

        if task is None:
            raise errors.NotFoundByName(name, TaskEntity)

        return task

    def get_by_list_and_syn_or_raise(
        self, lst: ListEntity, syn: FieldSlotStr
    ) -> TaskEntity:
        task = self._task_repo.get_by_list_id_and_syn(lst.list_id, syn)

        if task is None:
            raise errors.NotFoundBySyn(syn, TaskEntity)

        return task

    def get_convenient(
        self,
        community_name: CommunityNameStr | None,
        list_name: ListNameStr | None,
        task_syn: FieldSlotStr,
        task_only_by_name: bool,
    ) -> tuple[CommunityEntity, CommunityUserEntity, ListEntity, TaskEntity]:
        community, community_user, lst = self._list_access_service.get_convenient(
            community_name, list_name
        )
        task = (
            self.get_by_list_and_name_or_raise(lst, task_syn)
            if task_only_by_name
            else self.get_by_list_and_syn_or_raise(lst, task_syn)
        )

        return (community, community_user, lst, task)
