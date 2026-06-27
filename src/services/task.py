


from dataclasses import dataclass

from domain import errors
from domain.entities.task import TaskEntity
from domain.enums.attribute import AttributeType
from domain.enums.rank import CommunityRank
from domain.value_objects.attribute import AttributeSyn
from domain.value_objects.index import Index
from domain.value_objects.list import ListName
from domain.value_objects.task_attribute_slot import TaskAttributeSlot
from repositories.attribute import AttributeRepository
from repositories.attribute_collection_entry import AttributeCollectionEntryRepository
from repositories.dtos.task import TaskAliasInsert, TaskInsert
from repositories.task import TaskRepository
from repositories.task_attribute_slot import TaskAttributeSlotInsert, TaskAttributeSlotRepository
from services.attribute_value_mapping import AttributeValueMappingService
from services.contexts.interacting_user import InteractingUserContext
import typing as t

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

    def create(        
        self,
        name: TaskAttributeSlot,
        list_name: ListName | None,
        aliases: t.Sequence[TaskAttributeSlot],
        task_attribute_value_mapping: t.Mapping[AttributeSyn, t.Sequence[TaskAttributeSlot]]
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

        syns: tuple[TaskAttributeSlot, ...] = (name, *aliases)
        aliases.__len__
        if len(aliases) > community.limits.attribute_task_value_slot_count_max:
            raise errors.AliasCountLimitReached(
                community.limits.attribute_task_value_slot_count_max, name
            )

        # --- Verify Syn Uniquness Across Each Other And Across All Tasks --- #
        TaskAttributeSlot.raise_if_not_norm_unique(syns)

        existing_same_syn = self._task_repo.get_by_list_id_and_any_syn(
            lst.list_id, syns
        )

        if existing_same_syn is not None:
            raise errors.SynAlreadyTaken(*existing_same_syn)
        
        # --- Validate And Create Task Attribute Value Mapping --- #

        ATTRIBUTE_TYPES: t.Final[frozenset[AttributeType]] = frozenset({AttributeType.TASK})

        syn_to_attr = self._attribute_repo.get_syn_to_attribute_by_list_id(lst.list_id, ATTRIBUTE_TYPES)
        attr_id_to_collection = self._attribute_collection_entry_repo.get_grouped_collections_by_list_id(lst.list_id, ATTRIBUTE_TYPES)
        
        avm = self._attribute_value_mapping_service.validate_and_build(task_attribute_value_mapping, syn_to_attr, attr_id_to_collection)

        # --- Create Task ---
        task_entity = self._task_repo.create(
            TaskInsert(
                lst.list_id, name
            )
        )

        # --- Create Task Aliases ---
        self._task_repo.create_many_aliases(
            TaskAliasInsert(task_entity.task_id, lst.list_id, alias) for alias in aliases
        )

        # --- Create Task Attribute Slots ---
        if avm:
            inserts: list[TaskAttributeSlotInsert] = []

            for attr, value in avm.items():
                for i, slot in enumerate(value):
                    inserts.append(TaskAttributeSlotInsert(
                        task_entity.task_id,
                        attr.attribute_id,
                        Index(i),
                        slot
                    ))

            if inserts:
                _ = self._task_attribute_slot_repo.create_many(inserts)

        return task_entity


    def delete(self)