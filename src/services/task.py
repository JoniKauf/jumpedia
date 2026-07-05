import types as ts
import typing as t
from dataclasses import dataclass

from domain import errors
from domain.entities.community import CommunityEntity
from domain.entities.list import ListEntity
from domain.entities.member import MemberEntity
from domain.entities.task import TaskEntity
from domain.enums.attribute import AttributeType
from domain.enums.operation import Operation
from domain.enums.rank import CommunityRank
from domain.value_objects.attribute import AttributeSynStr
from domain.value_objects.community import CommunityNameStr
from domain.value_objects.field_slot import FieldSlotStr
from domain.value_objects.index import Index
from domain.value_objects.list import ListNameStr
from repositories.attribute import AttributeRepository
from repositories.collection_entry import CollectionEntryRepository
from repositories.dtos.task import TaskAliasInsert, TaskInsert
from repositories.field_slot import FieldSlotInsert, FieldSlotRepository
from repositories.task import TaskRepository
from services.contexts.interacting_user import InteractingUserContext
from services.dtos.task import DeletedTask, TaskInfo, TaskSummariesData, TaskSummary
from services.field_mapping import FieldMappingService
from services.list import ListAccessService
from services.permission import PermissionService


@dataclass(frozen=True, slots=True, eq=False)
class TaskService:
    _task_repo: TaskRepository
    _attribute_repo: AttributeRepository
    _permission_service: PermissionService
    _list_access_service: ListAccessService
    _field_mapping_service: FieldMappingService
    _collection_entry_repo: CollectionEntryRepository
    _field_slot_repo: FieldSlotRepository
    _task_access_service: TaskAccessService

    def create(
        self,
        name: FieldSlotStr,
        list_name: ListNameStr,
        aliases: t.Sequence[FieldSlotStr],
        field_mapping: t.Mapping[AttributeSynStr, t.Sequence[FieldSlotStr]],
    ) -> TaskEntity:
        # --- Get Data --- #
        community, member, lst = self._list_access_service.get_convenient(
            None, list_name
        )

        # --- Verify Rank --- #
        self._permission_service.ensure_community_rank(member, CommunityRank.HELPER)

        # --- Verify Limit Of Count Not Exceeded --- #
        task_count = self._task_repo.count_by_list(lst.list_id)

        if task_count >= community.limits.list_task_count_max:
            raise errors.CountLimitReached(
                community.limits.list_task_count_max, TaskEntity
            )

        syns: tuple[FieldSlotStr, ...] = (name, *aliases)

        if len(aliases) > community.limits.field_slot_count_max:
            raise errors.AliasCountLimitReached(
                community.limits.field_slot_count_max, name, tuple(aliases)
            )

        # --- Verify Syn Uniquness Across Each Other And Across All Tasks --- #
        FieldSlotStr.raise_if_not_unique(syns)

        existing_same_syn = self._task_repo.get_first_by_list_id_and_any_syn(
            lst.list_id, syns, None
        )

        if existing_same_syn is not None:
            colliding_task, colliding_syn = existing_same_syn

            raise errors.SynAlreadyTaken(*existing_same_syn, colliding_task.name != colliding_syn, colliding_syn != name)


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

        fm = self._field_mapping_service.validate_and_build(
            field_mapping, syn_to_attr, attr_id_to_collection
        )

        del field_mapping

        # --- Create Task ---
        task_entity = self._task_repo.create(TaskInsert(lst.list_id, name))

        # --- Create Task Aliases ---
        self._task_repo.create_many_aliases(
            TaskAliasInsert(task_entity.task_id, Index(i), lst.list_id, alias)
            for i, alias in enumerate(aliases)
        )

        # --- Create Task Attribute Slots ---
        if fm:
            inserts: list[FieldSlotInsert] = []

            for attr, field in fm.items():
                for i, slot in enumerate(field):
                    inserts.append(
                        FieldSlotInsert(
                            task_entity.task_id, attr.attribute_id, Index(i), slot
                        )
                    )

            if inserts:
                _ = self._field_slot_repo.create_many(inserts)

        return task_entity

    def delete(self, name: FieldSlotStr, list_name: ListNameStr) -> DeletedTask:
        _, member, lst, task = self._task_access_service.get_convenient(
            None, list_name, name, True
        )

        self._permission_service.ensure_community_rank(member, CommunityRank.MODERATOR)

        self._task_repo.delete(task.task_id)

        return DeletedTask(task.name, lst)
    
    def edit_name(self, current_name: FieldSlotStr, new_name: FieldSlotStr, list_name: ListNameStr) -> FieldSlotStr:
        _, member, lst, task = self._task_access_service.get_convenient(
            None, list_name, current_name, True
        )

        self._permission_service.ensure_community_rank(
            member, CommunityRank.MODERATOR
        )

        # Exactly equal (real matches, not just norm)
        if task.name.real == new_name.real:
            raise errors.NameNotDifferent(current_name)

        existing_task_and_syn = self._task_repo.get_by_list_id_and_syn(
            lst.list_id, new_name, 
        )

        if existing_task_and_syn is not None:
            existing_task, existing_syn = existing_task_and_syn

            # False if the current task has the same name but with different casing
            if not (existing_task == task and task.name == existing_syn):
                raise errors.SynAlreadyTaken(existing_task, new_name, existing_task.name != existing_syn, False)

        self._task_repo.update_name(task.task_id, new_name)
        
        return task.name

    def edit_aliases(
        self,
        name: FieldSlotStr,
        new_aliases: tuple[FieldSlotStr, ...],
        list_name: ListNameStr,
        operation: Operation,
    ) -> TaskEntity:
        community, member, lst, task = self._task_access_service.get_convenient(
            None, list_name, name, True
        )

        self._permission_service.ensure_community_rank(
            member, CommunityRank.MODERATOR
        )

        FieldSlotStr.raise_if_not_unique(new_aliases)

        current_aliases = self._task_repo.get_aliases_by_task_id(task.task_id)
    
        if operation is Operation.COMBINE:
            new_aliases = tuple(dict.fromkeys((*new_aliases, *current_aliases)))
        
        # If aliases exactly equal to existing ones (including order even tho technically unimportant)
        if current_aliases == new_aliases:
            raise errors.AliasesNotDifferent(new_aliases)

        if len(new_aliases) > community.limits.field_slot_count_max:
            raise errors.AliasCountLimitReached(
                community.limits.field_slot_count_max, task.name, new_aliases
            )
        
        # Check if name collision with current task
        for alias in new_aliases:
            if alias == task.name:
                raise errors.SynAlreadyTaken(task, alias, False, True)

        existing_task_and_syn = self._task_repo.get_first_by_list_id_and_any_syn(
            lst.list_id, new_aliases, task.task_id
        )

        # Check syn collision for other tasks (collisions with aliases of current task are allowed)
        if existing_task_and_syn is not None:
            existing_task, existing_syn = existing_task_and_syn

            raise errors.SynAlreadyTaken(existing_task, existing_syn, existing_task.name != existing_syn, True)
        
        self._task_repo.update_aliases(
            task.task_id,
            (
                TaskAliasInsert(task.task_id, Index(i), lst.list_id, alias)
                for i, alias in enumerate(new_aliases)
            ),
        )

        return task

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
        tup = self._task_repo.get_by_list_id_and_syn(lst.list_id, syn)

        if tup is None:
            raise errors.NotFoundBySyn(syn, TaskEntity)

        return tup[0]

    def get_convenient(
        self,
        community_name: CommunityNameStr | None,
        list_name: ListNameStr | None,
        task_syn: FieldSlotStr,
        task_only_by_name: bool,
    ) -> tuple[CommunityEntity, MemberEntity, ListEntity, TaskEntity]:
        community, member, lst = self._list_access_service.get_convenient(
            community_name, list_name
        )
        task = (
            self.get_by_list_and_name_or_raise(lst, task_syn)
            if task_only_by_name
            else self.get_by_list_and_syn_or_raise(lst, task_syn)
        )

        return (community, member, lst, task)
