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
from domain.value_objects.attribute import AttributeSynStr
from domain.value_objects.community import CommunityNameStr
from domain.value_objects.index import Index
from domain.value_objects.list import ListNameStr
from domain.value_objects.task_attribute_slot import TaskAttributeSlotStr
from repositories.attribute import AttributeRepository
from repositories.attribute_collection_entry import AttributeCollectionEntryRepository
from repositories.dtos.task import TaskAliasInsert, TaskInsert
from repositories.task import TaskRepository
from repositories.task_attribute_slot import (
    TaskAttributeSlotInsert,
    TaskAttributeSlotRepository,
)
from services.attribute_value_mapping import AttributeValueMappingService
from services.contexts.interacting_user import InteractingUserContext
from services.dtos.task import DeletedTask, TaskInfo, TaskSummary
from services.list import ListAccessService
from services.permission import PermissionService


@dataclass(frozen=True, slots=True, eq=False)
class TaskService:
    _ctx: InteractingUserContext
    _task_repo: TaskRepository
    _attribute_repo: AttributeRepository
    _permission_service: PermissionService
    _list_access_service: ListAccessService
    _attribute_value_mapping_service: AttributeValueMappingService
    _attribute_collection_entry_repo: AttributeCollectionEntryRepository
    _task_attribute_slot_repo: TaskAttributeSlotRepository
    _task_access_service: TaskAccessService

    def create(
        self,
        name: TaskAttributeSlotStr,
        list_name: ListNameStr,
        aliases: t.Sequence[TaskAttributeSlotStr],
        task_attribute_value_mapping: t.Mapping[
            AttributeSynStr, t.Sequence[TaskAttributeSlotStr]
        ],
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

        syns: tuple[TaskAttributeSlotStr, ...] = (name, *aliases)

        if len(aliases) > community.limits.attribute_task_value_slot_count_max:
            raise errors.AliasCountLimitReached(
                community.limits.attribute_task_value_slot_count_max, name
            )

        # --- Verify Syn Uniquness Across Each Other And Across All Tasks --- #
        TaskAttributeSlotStr.raise_if_not_norm_unique(syns)

        existing_same_syn = self._task_repo.get_by_list_id_and_any_syn(
            lst.list_id, syns
        )

        if existing_same_syn is not None:
            raise errors.SynAlreadyTaken(*existing_same_syn)

        # --- Validate And Create Task Attribute Value Mapping --- #

        ATTRIBUTE_TYPES: t.Final[frozenset[AttributeType]] = frozenset(
            {AttributeType.TASK}
        )

        syn_to_attr = self._attribute_repo.get_syn_to_attribute_by_list_id(
            lst.list_id, ATTRIBUTE_TYPES
        )
        attr_id_to_collection = (
            self._attribute_collection_entry_repo.get_grouped_collections_by_list_id(
                lst.list_id, ATTRIBUTE_TYPES
            )
        )

        avm = self._attribute_value_mapping_service.validate_and_build(
            task_attribute_value_mapping, syn_to_attr, attr_id_to_collection
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
            inserts: list[TaskAttributeSlotInsert] = []

            for attr, value in avm.items():
                for i, slot in enumerate(value):
                    inserts.append(
                        TaskAttributeSlotInsert(
                            task_entity.task_id, attr.attribute_id, Index(i), slot
                        )
                    )

            if inserts:
                _ = self._task_attribute_slot_repo.create_many(inserts)

        return task_entity

    def delete(self, name: TaskAttributeSlotStr, list_name: ListNameStr) -> DeletedTask:
        _, community_user, lst = self._list_access_service.get_convenient(
            None, list_name
        )

        self._permission_service.ensure_community_rank(
            community_user, CommunityRank.MODERATOR
        )

        task = self._task_access_service.get_by_list_and_name_or_raise(lst, name)

        self._task_repo.delete(task.task_id)

        return DeletedTask(task.name, lst)


@dataclass(frozen=True, slots=True, eq=False)
class TaskQueryService:
    _task_access_service: TaskAccessService
    _task_repo: TaskRepository
    _attribute_repo: AttributeRepository
    _task_attribute_slot_repo: TaskAttributeSlotRepository
    _list_access_service: ListAccessService

    def info(
        self, syn: TaskAttributeSlotStr, list_name: ListNameStr | None
    ) -> TaskInfo:
        _, _, lst, task = self._task_access_service.get_convenient(None, list_name, syn)

        ATTRIBUTE_TYPES: t.Final = {AttributeType.TASK}

        id_to_attr = self._attribute_repo.get_all_by_list_id(
            lst.list_id, ATTRIBUTE_TYPES
        )

        aliases = self._task_repo.get_aliases_by_task_id(task.task_id)
        task_attribute_value_mapping = (
            self._task_attribute_slot_repo.get_attribute_value_mapping_by_task_id(
                task.task_id, ATTRIBUTE_TYPES
            )
        )

        return TaskInfo(
            task.task_id,
            task.name,
            aliases,
            lst,
            ts.MappingProxyType(
                {
                    id_to_attr[k]: tuple(slot.slot for slot in v)
                    for k, v in task_attribute_value_mapping.items()
                }
            ),
        )

    def summaries(self, list_name: ListNameStr | None) -> tuple[TaskSummary, ...]:
        _, _, lst = self._list_access_service.get_convenient(None, list_name)

        ATTRIBUTE_TYPES: t.Final = {AttributeType.TASK}

        id_to_attr = self._attribute_repo.get_all_by_list_id(
            lst.list_id, ATTRIBUTE_TYPES
        )

        tasks = self._task_repo.get_all_by_list_id(lst.list_id)
        task_id_to_aliases = self._task_repo.get_grouped_aliases_by_list_id(lst.list_id)
        task_id_to_task_attribute_value_mapping = (
            self._task_attribute_slot_repo.get_attribute_value_mapping_by_list_id(
                lst.list_id, ATTRIBUTE_TYPES
            )
        )

        return tuple(
            TaskSummary(
                task.task_id,
                task.name,
                task_id_to_aliases[task.task_id],
                lst,
                ts.MappingProxyType(
                    {
                        id_to_attr[k]: tuple(slot.slot for slot in v)
                        for k, v in task_id_to_task_attribute_value_mapping[
                            task.task_id
                        ].items()
                    }
                ),
            )
            for task in tasks
        )


@dataclass(frozen=True, slots=True, eq=False)
class TaskAccessService:
    _ctx: InteractingUserContext
    _task_repo: TaskRepository
    _list_access_service: ListAccessService

    def get_by_list_and_name_or_raise(
        self, lst: ListEntity, name: TaskAttributeSlotStr
    ) -> TaskEntity:
        task = self._task_repo.get_by_list_id_and_name(lst.list_id, name)

        if task is None:
            raise errors.NotFoundByName(name, TaskEntity)

        return task

    def get_by_list_and_syn_or_raise(
        self, lst: ListEntity, syn: TaskAttributeSlotStr
    ) -> TaskEntity:
        task = self._task_repo.get_by_list_id_and_syn(lst.list_id, syn)

        if task is None:
            raise errors.NotFoundBySyn(syn, TaskEntity)

        return task

    def get_convenient(
        self,
        community_name: CommunityNameStr | None,
        list_name: ListNameStr | None,
        task_syn: TaskAttributeSlotStr,
    ) -> tuple[CommunityEntity, CommunityUserEntity, ListEntity, TaskEntity]:
        community, community_user, lst = self._list_access_service.get_convenient(
            community_name, list_name
        )
        task = self.get_by_list_and_syn_or_raise(lst, task_syn)

        return (community, community_user, lst, task)
