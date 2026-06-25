


from dataclasses import dataclass

from domain import errors
from domain.entities.attribute import AttributeEntity
from domain.entities.task import TaskEntity
from domain.enums.attribute import AttributeType
from domain.enums.rank import CommunityRank
from domain.value_objects.attribute import AttributeSyn
from domain.value_objects.list import ListName
from domain.value_objects.task_value_slot import TaskValueSlot
from repositories.attribute import AttributeRepository
from repositories.task import TaskRepository
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

    def create(        
        self,
        name: TaskValueSlot,
        list_name: ListName | None,
        aliases: tuple[TaskValueSlot, ...],
        task_attribute_value_mapping: t.Mapping[AttributeSyn, tuple[TaskValueSlot, ...]]
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
        task_count = self._task_repo.count_by_list(lst.id)

        if task_count >= community.limits.list_task_count_max:
            raise errors.CountLimitReached(
                community.limits.list_task_count_max, TaskEntity
            )

        syns: tuple[TaskValueSlot, ...] = (name, *aliases)

        if len(aliases) > community.limits.attribute_task_value_slot_count_max:
            raise errors.AliasCountLimitReached(
                community.limits.attribute_task_value_slot_count_max, name
            )

        # --- Verify Syn Uniquness Across Each Other And Across All Tasks --- #
        TaskValueSlot.raise_if_not_norm_unique(syns)

        existing_same_syn = self._task_repo.get_by_list_id_and_any_syn(
            lst.id, syns
        )

        if existing_same_syn is not None:
            raise errors.SynAlreadyTaken(*existing_same_syn)
        
        # --- Validate Task Attribute Value Mapping --- #

        syn_to_attr = self._attribute_repo.get_syn_to_attribute_by_list_id(lst.id, {AttributeType.TASK})

        avm = self._attribute_value_mapping_service.validate_and_build(task_attribute_value_mapping, syn_to_attr)

        # --- Create Attribute ---
        attr_entity = self._attribute_repo.create(
            AttributeInsert(
                lst._id, name, type, AttributeKind.NONE, slot, task_count + 1
            )
        )

        # --- Create Attribute Aliases ---
        self._attribute_repo.create_many_aliases(
            AttributeAliasInsert(attr_entity.id, lst.id, alias) for alias in aliases
        )

        # --- Create Attribute Collection ---
        if collection_entries:
            created_entries: list[AttributeCollectionEntryEntity] = (
                self._attribute_collection_entry_repo.create_many(
                    AttributeCollectionEntryInsert(attr_entity.id, i, entry.value)
                    for i, entry in enumerate(collection_entries)
                )
            )

            all_aliases: list[AttributeCollectionEntryAliasInsert] = []

            for i, created_entry in enumerate(created_entries):
                for alias in collection_entries[i].aliases:
                    alias_insert = AttributeCollectionEntryAliasInsert(
                        created_entry.id, created_entry.attribute_id, alias
                    )

                    all_aliases.append(alias_insert)

            self._attribute_collection_entry_repo.create_many_aliases(all_aliases)

        return attr_entity
