import typing as t
from dataclasses import dataclass

from jumpedia.domain.entities.attribute import AttributeEntity
from jumpedia.domain.entities.community import CommunityEntity
from jumpedia.domain.entities.list import ListEntity
from jumpedia.domain.entities.member import MemberEntity
from jumpedia.domain.entities.task import TaskEntity
from jumpedia.domain.enums.attribute import AttributeKind, AttributeType
from jumpedia.domain.enums.concept import Concept
from jumpedia.domain.enums.edit_mode import AliasEditMode, FieldMappingEditMode
from jumpedia.domain.enums.rank import CommunityRank
from jumpedia.domain.errors.business import (
    AliasCountLimitSurpassed,
    AliasesDidNotChange,
    CountLimitReached,
    NewNameEqualToCurrent,
    NotFoundByName,
    NotFoundBySyn,
    SynAlreadyTaken,
)
from jumpedia.domain.sentinels.default import DEFAULT
from jumpedia.domain.typing.attribute import SlotTypeT, TaskAttributeTypeT
from jumpedia.domain.typing.field_mapping import (
    RawFieldMappingT,
)
from jumpedia.domain.value_objects.attribute import AttributeSynStr
from jumpedia.domain.value_objects.community import CommunityNameStr
from jumpedia.domain.value_objects.field_slot import FieldSlotStr
from jumpedia.domain.value_objects.filter import FilterT
from jumpedia.domain.value_objects.index import Index
from jumpedia.domain.value_objects.list import ListNameStr

lazy from jumpedia.repositories.attribute import AttributeRepository
lazy from jumpedia.repositories.collection_entry import CollectionEntryRepository
from jumpedia.repositories.dtos.field_slot import FieldSlotInsert
from jumpedia.repositories.dtos.task import TaskAliasInsert, TaskInsert

lazy from jumpedia.repositories.field_slot import FieldSlotRepository
lazy from jumpedia.repositories.task import TaskRepository
from jumpedia.services.dtos.task import PreparedDeleteTask, TaskInfo

lazy from jumpedia.services.internal.edit_mode import EditModeService
lazy from jumpedia.services.internal.field_mapping import (
    FieldMappingBuildService,
    FieldMappingService,
)
lazy from jumpedia.services.internal.permission import PermissionService
lazy from jumpedia.services.internal.strs import StrsService
lazy from jumpedia.services.list import ListAccessService


@dataclass(frozen=True, slots=True, eq=False)
class TaskService:
    _attribute_repository: AttributeRepository
    _collection_entry_repository: CollectionEntryRepository
    _field_slot_repository: FieldSlotRepository
    _task_repository: TaskRepository

    _edit_mode_service: EditModeService
    _field_mapping_build_service: FieldMappingBuildService
    _list_access_service: ListAccessService
    _permission_service: PermissionService
    _strs_service: StrsService
    _task_access_service: TaskAccessService

    def create(
        self,
        task_name: FieldSlotStr,
        list_name: ListNameStr,
        aliases: t.Sequence[FieldSlotStr],
        field_mapping: RawFieldMappingT,
    ) -> TaskEntity:
        # --- Get Data --- #
        community, member, lst = self._list_access_service.get_convenient(
            DEFAULT, list_name
        )

        # --- Verify Rank --- #
        self._permission_service.ensure_community_rank(member, CommunityRank.HELPER)

        # --- Verify Limit Of Count Not Exceeded --- #
        task_count = self._task_repository.count_by_list(lst.list_id)

        if task_count >= community.limits.list_task_count_max:
            raise CountLimitReached(Concept.TASK, community.limits.list_task_count_max)

        syns: tuple[FieldSlotStr, ...] = (task_name, *aliases)

        if len(aliases) > community.limits.field_slot_count_max:
            raise AliasCountLimitSurpassed(
                community.limits.field_slot_count_max, task_name, tuple(aliases)
            )

        # --- Verify Syn Uniquness Across Each Other And Across All Tasks --- #
        self._strs_service.validate_unique_syns(syns, Concept.TASK)

        existing_same_syn = self._task_repository.get_first_by_list_id_and_any_syn(
            lst.list_id, syns, None
        )

        if existing_same_syn is not None:
            colliding_task, colliding_syn = existing_same_syn

            raise SynAlreadyTaken(
                *existing_same_syn,
                colliding_task.name != colliding_syn,
                colliding_syn != task_name,
            )

        # --- Validate And Create Task Attribute Value Mapping --- #

        ATTRIBUTE_TYPES: t.Final = AttributeType.TASK.as_set()
        ATTRIBUTE_KINDS: t.Final = AttributeKind.NONE_KINDED

        syn_to_attr = self._attribute_repository.get_syn_to_attribute_by_list_id(
            lst.list_id, ATTRIBUTE_TYPES, ATTRIBUTE_KINDS
        )
        attr_id_to_collection = (
            self._collection_entry_repository.get_grouped_collections_by_list_id(
                lst.list_id, ATTRIBUTE_TYPES, ATTRIBUTE_KINDS
            )
        )

        fm = self._field_mapping_build_service.build_raw(
            field_mapping, syn_to_attr, attr_id_to_collection
        )

        del field_mapping

        # --- Create Task ---
        task_entity = self._task_repository.create(TaskInsert(lst.list_id, task_name))

        # --- Create Task Aliases ---
        self._task_repository.create_many_aliases(
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
                _ = self._field_slot_repository.create_many(inserts)

        return task_entity

    def delete(self, prepared: PreparedDeleteTask) -> None:
        self._task_repository.delete(prepared.task_id)

    def edit_name(
        self, task_name: FieldSlotStr, new_name: FieldSlotStr, list_name: ListNameStr
    ) -> FieldSlotStr:
        _, member, lst, task = self._task_access_service.get_convenient(
            DEFAULT, list_name, task_name, True
        )

        self._permission_service.ensure_community_rank(member, CommunityRank.MODERATOR)

        # Exactly equal (real matches, not just norm)
        if task.name.real == new_name.real:
            raise NewNameEqualToCurrent(task)

        existing_task_and_syn = self._task_repository.get_by_list_id_and_syn(
            lst.list_id,
            new_name,
        )

        if existing_task_and_syn is not None:
            existing_task, existing_syn = existing_task_and_syn

            # False if the current task has the same name but with different casing
            if not (existing_task == task and task.name == existing_syn):
                raise SynAlreadyTaken(
                    existing_task, new_name, existing_task.name != existing_syn, False
                )

        self._task_repository.update_name(task.task_id, new_name)

        return task.name

    def edit_aliases(
        self,
        new_aliases: tuple[FieldSlotStr, ...],
        edit_mode: AliasEditMode,
        task_name: FieldSlotStr,
        list_name: ListNameStr,
    ) -> TaskEntity:
        community, member, lst, task = self._task_access_service.get_convenient(
            DEFAULT, list_name, task_name, True
        )

        self._permission_service.ensure_community_rank(member, CommunityRank.MODERATOR)

        self._strs_service.validate_unique_aliases(new_aliases, Concept.TASK)

        current_aliases = self._task_repository.get_aliases_by_task_id(task.task_id)

        new_aliases = self._edit_mode_service.handle_alias_edit(
            edit_mode, current_aliases, new_aliases, Concept.TASK
        )

        # If aliases exactly equal to existing ones (including order even tho technically unimportant)
        if FieldSlotStr.sequence_real_equals(current_aliases, new_aliases):
            raise AliasesDidNotChange(task, new_aliases)

        del current_aliases

        if len(new_aliases) > community.limits.field_slot_count_max:
            raise AliasCountLimitSurpassed(
                community.limits.field_slot_count_max, task.name, new_aliases
            )

        # Check if name collision with current task
        for alias in new_aliases:
            if alias == task.name:
                raise SynAlreadyTaken(task, alias, False, True)

        existing_task_and_syn = self._task_repository.get_first_by_list_id_and_any_syn(
            lst.list_id, new_aliases, task.task_id
        )

        # Check syn collision for other tasks (collisions with aliases of current task are allowed)
        if existing_task_and_syn is not None:
            existing_task, existing_syn = existing_task_and_syn

            raise SynAlreadyTaken(
                existing_task, existing_syn, existing_task.name != existing_syn, True
            )

        self._task_repository.update_aliases(
            task.task_id,
            (
                TaskAliasInsert(task.task_id, Index(i), lst.list_id, alias)
                for i, alias in enumerate(new_aliases)
            ),
        )

        return task

    def edit_field_mapping(
        self,
        new_field_mapping: RawFieldMappingT,
        edit_mode: FieldMappingEditMode,
        task_name: FieldSlotStr,
        list_name: ListNameStr,
    ) -> TaskEntity:
        _, member, lst, task = self._task_access_service.get_convenient(
            DEFAULT, list_name, task_name, True
        )

        self._permission_service.ensure_community_rank(member, CommunityRank.MODERATOR)

        ATTRIBUTE_TYPES: t.Final = AttributeType.TASK.as_set()
        ATTRIBUTE_KINDS: t.Final = AttributeKind.NONE_KINDED

        syn_to_attr = self._attribute_repository.get_syn_to_attribute_by_list_id(
            lst.list_id, ATTRIBUTE_TYPES, ATTRIBUTE_KINDS
        )

        attr_id_to_collection = (
            self._collection_entry_repository.get_grouped_collections_by_list_id(
                lst.list_id, ATTRIBUTE_TYPES, ATTRIBUTE_KINDS
            )
        )
        id_to_attr = {attr.attribute_id: attr for attr in syn_to_attr.values()}

        new_fm = self._field_mapping_build_service.build_edit(
            edit_mode,
            {
                id_to_attr[attr_id]: field
                for attr_id, field in self._field_slot_repository.get_field_mapping_by_task_id(
                    task.task_id
                ).items()
            },
            new_field_mapping,
            syn_to_attr,
            attr_id_to_collection,
        )

        self._field_slot_repository.replace_all_by_task_id(
            task.task_id,
            (
                FieldSlotInsert(task.task_id, attr.attribute_id, Index(i), slot)
                for attr, field in new_fm.items()
                for i, slot in enumerate(field)
            ),
        )

        return task


@dataclass(frozen=True, slots=True, eq=False)
class TaskPrepareService:
    _permission_service: PermissionService
    _task_access_service: TaskAccessService

    def delete(
        self, task_name: FieldSlotStr, list_name: ListNameStr
    ) -> tuple[PreparedDeleteTask, ListEntity, TaskEntity]:
        _, member, lst, task = self._task_access_service.get_convenient(
            DEFAULT, list_name, task_name, True
        )

        self._permission_service.ensure_community_rank(member, CommunityRank.MODERATOR)

        return PreparedDeleteTask(task.task_id), lst, task


@dataclass(frozen=True, slots=True, eq=False)
class TaskQueryService:
    _field_mapping_service: FieldMappingService

    def get_info(self, syn: FieldSlotStr, list_name: ListNameStr | DEFAULT) -> TaskInfo:
        return self._field_mapping_service.get_info(syn, list_name)

    def get_summaries(
        self,
        filter: FilterT | None,
        sort: t.Sequence[tuple[AttributeSynStr, bool]],
        yield_: t.Sequence[AttributeSynStr],
        list_name: ListNameStr | DEFAULT,
    ) -> frozendict[
        AttributeEntity[TaskAttributeTypeT],
        tuple[tuple[SlotTypeT, ...], ...],
    ]:
        return self._field_mapping_service.get_summaries(
            filter, sort, yield_, list_name
        )


@dataclass(frozen=True, slots=True, eq=False)
class TaskAccessService:
    _task_repository: TaskRepository

    _list_access_service: ListAccessService

    def get_by_list_and_name_or_raise(
        self, lst: ListEntity, name: FieldSlotStr
    ) -> TaskEntity:
        task = self._task_repository.get_by_list_id_and_name(lst.list_id, name)

        if task is None:
            raise NotFoundByName(Concept.TASK, name)

        return task

    def get_by_list_and_syn_or_raise(
        self, lst: ListEntity, syn: FieldSlotStr
    ) -> TaskEntity:
        tup = self._task_repository.get_by_list_id_and_syn(lst.list_id, syn)

        if tup is None:
            raise NotFoundBySyn(Concept.TASK, syn)

        return tup[0]

    def get_convenient(
        self,
        community_name: CommunityNameStr | DEFAULT,
        list_name: ListNameStr | DEFAULT,
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
