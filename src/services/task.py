import typing as t
from dataclasses import dataclass

from domain.entities.attribute import AttributeEntity
from domain.entities.community import CommunityEntity
from domain.entities.list import ListEntity
from domain.entities.member import MemberEntity
from domain.entities.task import TaskEntity
from domain.enums.attribute import AttributeType
from domain.enums.edit_mode import AliasEditMode, FieldMappingEditMode
from domain.enums.rank import CommunityRank
from domain.errors import business
from domain.sentinels.default import DEFAULT
from domain.types.attribute import NonUserAttributeTypeT, SlotTypeT
from domain.types.field_mapping import (
    FrozenFieldMappingEntityToStrings,
    RawFieldMappingT,
)
from domain.value_objects.attribute import AttributeSynStr
from domain.value_objects.community import CommunityNameStr
from domain.value_objects.field_slot import FieldSlotStr
from domain.value_objects.filter import FilterT
from domain.value_objects.index import Index
from domain.value_objects.list import ListNameStr
from repositories.attribute import AttributeRepository
from repositories.collection_entry import CollectionEntryRepository
from repositories.dtos.task import TaskAliasInsert, TaskInsert
from repositories.field_slot import FieldSlotInsert, FieldSlotRepository
from repositories.task import TaskRepository
from services.contexts.interacting_user import InteractingUserContext
from services.dtos.task import PreparedDeleteTask
from services.internal.edit_mode import EditModeService
from services.internal.field_mapping import FieldMappingService
from services.internal.permission import PermissionService
from services.internal.slot_type import SlotTypeService
from services.list import ListAccessService


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
    _edit_mode_service: EditModeService

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
        task_count = self._task_repo.count_by_list(lst.list_id)

        if task_count >= community.limits.list_task_count_max:
            raise business.CountLimitReached(
                community.limits.list_task_count_max, TaskEntity
            )

        syns: tuple[FieldSlotStr, ...] = (task_name, *aliases)

        if len(aliases) > community.limits.field_slot_count_max:
            raise business.AliasCountLimitReached(
                community.limits.field_slot_count_max, task_name, tuple(aliases)
            )

        # --- Verify Syn Uniquness Across Each Other And Across All Tasks --- #
        FieldSlotStr.raise_if_not_unique(syns)

        existing_same_syn = self._task_repo.get_first_by_list_id_and_any_syn(
            lst.list_id, syns, None
        )

        if existing_same_syn is not None:
            colliding_task, colliding_syn = existing_same_syn

            raise business.SynAlreadyTaken(
                *existing_same_syn,
                colliding_task.name != colliding_syn,
                colliding_syn != task_name,
            )

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

        fm = self._field_mapping_service.build_raw(
            field_mapping, syn_to_attr, attr_id_to_collection
        )

        del field_mapping

        # --- Create Task ---
        task_entity = self._task_repo.create(TaskInsert(lst.list_id, task_name))

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

    def delete(self, prepared: PreparedDeleteTask) -> None:
        self._task_repo.delete(prepared.task_id)

    def edit_name(
        self, new_name: FieldSlotStr, task_name: FieldSlotStr, list_name: ListNameStr
    ) -> FieldSlotStr:
        _, member, lst, task = self._task_access_service.get_convenient(
            DEFAULT, list_name, task_name, True
        )

        self._permission_service.ensure_community_rank(member, CommunityRank.MODERATOR)

        # Exactly equal (real matches, not just norm)
        if task.name.real == new_name.real:
            raise business.NameNotDifferent(task_name)

        existing_task_and_syn = self._task_repo.get_by_list_id_and_syn(
            lst.list_id,
            new_name,
        )

        if existing_task_and_syn is not None:
            existing_task, existing_syn = existing_task_and_syn

            # False if the current task has the same name but with different casing
            if not (existing_task == task and task.name == existing_syn):
                raise business.SynAlreadyTaken(
                    existing_task, new_name, existing_task.name != existing_syn, False
                )

        self._task_repo.update_name(task.task_id, new_name)

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

        FieldSlotStr.raise_if_not_unique(new_aliases)

        current_aliases = self._task_repo.get_aliases_by_task_id(task.task_id)

        new_aliases = self._edit_mode_service.handle_alias_edit(
            edit_mode, current_aliases, new_aliases
        )

        # If aliases exactly equal to existing ones (including order even tho technically unimportant)
        if FieldSlotStr.sequences_requal(current_aliases, new_aliases):
            raise business.AliasesNotDifferent(new_aliases)

        del current_aliases

        if len(new_aliases) > community.limits.field_slot_count_max:
            raise business.AliasCountLimitReached(
                community.limits.field_slot_count_max, task.name, new_aliases
            )

        # Check if name collision with current task
        for alias in new_aliases:
            if alias == task.name:
                raise business.SynAlreadyTaken(task, alias, False, True)

        existing_task_and_syn = self._task_repo.get_first_by_list_id_and_any_syn(
            lst.list_id, new_aliases, task.task_id
        )

        # Check syn collision for other tasks (collisions with aliases of current task are allowed)
        if existing_task_and_syn is not None:
            existing_task, existing_syn = existing_task_and_syn

            raise business.SynAlreadyTaken(
                existing_task, existing_syn, existing_task.name != existing_syn, True
            )

        self._task_repo.update_aliases(
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

        syn_to_attr = self._attribute_repo.get_syn_to_attribute_by_list_id(
            lst.list_id, ATTRIBUTE_TYPES
        )
        attr_id_to_collection = (
            self._collection_entry_repo.get_grouped_collections_by_list_id(
                lst.list_id, ATTRIBUTE_TYPES
            )
        )

        new_fm = self._field_mapping_service.build_edit(
            edit_mode,
            self._field_slot_repo.get_field_mapping_by_task_id(task.task_id),
            new_field_mapping,
            syn_to_attr,
            attr_id_to_collection,
        )

        self._field_slot_repo.replace_all_by_task_id(
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
    _task_access_service: TaskAccessService
    _permission_service: PermissionService

    def delete(self, task_name: FieldSlotStr, list_name: ListNameStr) -> tuple[PreparedDeleteTask, ListEntity, TaskEntity]:
        _, member, lst, task = self._task_access_service.get_convenient(
            DEFAULT, list_name, task_name, True
        )

        self._permission_service.ensure_community_rank(member, CommunityRank.MODERATOR)

        return PreparedDeleteTask(task.task_id), lst, task


@dataclass(frozen=True, slots=True, eq=False)
class TaskQueryService:
    _task_access_service: TaskAccessService
    _task_repo: TaskRepository
    _attribute_repo: AttributeRepository
    _field_slot_repo: FieldSlotRepository
    _list_access_service: ListAccessService
    _collection_entry_repo: CollectionEntryRepository
    _field_mapping_service: FieldMappingService
    _slot_type_service: SlotTypeService

    def get_info(
        self, syn: FieldSlotStr, list_name: ListNameStr | DEFAULT
    ) -> FrozenFieldMappingEntityToStrings[NonUserAttributeTypeT]:
        _, _, lst, task = self._task_access_service.get_convenient(
            DEFAULT, list_name, syn, False
        )

        ATTRIBUTE_TYPES: t.Final = AttributeType.NON_USER()

        attrs = self._attribute_repo.get_all_by_list_id_ordered_by_position(
            lst.list_id, ATTRIBUTE_TYPES
        )

        # --- Get Static Field Mapping --- #
        static_field_mapping = (
            self._field_mapping_service.get_static_field_mapping_single(
                task, self._task_repo.get_aliases_by_task_id(task.task_id), attrs
            )
        )

        task_field_mapping = self._field_slot_repo.get_field_mapping_by_task_id(
            task.task_id
        )

        field_mapping = static_field_mapping | task_field_mapping

        del static_field_mapping, task_field_mapping

        return frozendict(
            (attr, field_mapping.get(attr.attribute_id, ())) for attr in attrs
        )

    def get_summaries(
        self,
        filter: FilterT | None,
        sort: t.Sequence[tuple[AttributeSynStr, bool]],
        yield_: t.Sequence[AttributeSynStr],
        list_name: ListNameStr | DEFAULT,
    ) -> frozendict[
        AttributeEntity[NonUserAttributeTypeT],
        tuple[tuple[SlotTypeT, ...], ...],
    ]:
        _, _, lst = self._list_access_service.get_convenient(DEFAULT, list_name)

        ATTRIBUTES_TYPES: t.Final = AttributeType.NON_USER()

        syn_to_attr = self._attribute_repo.get_syn_to_attribute_by_list_id(
            lst.list_id, ATTRIBUTES_TYPES
        )
        attrs_sorted = tuple(
            sorted(set(syn_to_attr.values()), key=lambda attr: attr.position.value)
        )
        attrs_sorted_to_yield = attrs_sorted

        if yield_:
            attrs_sorted_to_yield = tuple(syn_to_attr[syn] for syn in yield_)

            if len(set(attrs_sorted_to_yield)) < len(attrs_sorted_to_yield):
                raise ValueError("Not unique")

        # Static field mapping is guaranteed to include all tasks. Use it as a basis
        # for iteration later, so we don't exclude any tasks if they don't have a
        # specific field mapping.
        task_id_to_static_field_mapping = (
            self._field_mapping_service.get_static_field_mapping_many(
                self._task_repo.get_all_by_list_id(lst.list_id),
                self._task_repo.get_grouped_aliases_by_list_id(lst.list_id),
                attrs_sorted,
            )
        )

        task_id_to_task_field_mapping = (
            self._field_slot_repo.get_task_field_mapping_by_list_id(lst.list_id)
        )

        # Combine all 3 mappings into the final one
        field_mappings_untyped = (
            (
                frozendict(static_field_mapping)
                | task_id_to_task_field_mapping.get(task_id, frozendict())
            )
            for task_id, static_field_mapping in task_id_to_static_field_mapping.items()
        )

        del task_id_to_static_field_mapping, task_id_to_task_field_mapping

        attr_id_to_slot_type = {
            attr.attribute_id: attr.field_config.slot_type for attr in attrs_sorted
        }

        field_mappings = tuple(
            {
                attr_id: tuple(
                    self._slot_type_service.many_to_slot_type(
                        f, attr_id_to_slot_type[attr_id], validate=False
                    )
                )
                for attr_id, f in fm.items()
            }
            for fm in field_mappings_untyped
        )
        attr_id_to_coll_value_to_idx = {
            attr_id: {
                slot_type: idx
                for slot_type, idx in zip(
                    self._slot_type_service.many_to_slot_type(
                        value_to_idx, attr_id_to_slot_type[attr_id], validate=False
                    ),
                    value_to_idx.values(),
                )
            }
            for attr_id, value_to_idx in self._collection_entry_repo.get_grouped_value_to_index_by_list_id(
                lst.list_id, AttributeType.TASK.as_set()
            ).items()
        }

        field_mappings = self._field_mapping_service.filter_and_sort(
            field_mappings, filter, sort, syn_to_attr, attr_id_to_coll_value_to_idx
        )

        return frozendict(
            (
                attr,
                tuple(
                    field_mapping[attr.attribute_id] for field_mapping in field_mappings
                ),
            )
            for attr in attrs_sorted_to_yield
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
            raise business.NotFoundByName(name, TaskEntity)

        return task

    def get_by_list_and_syn_or_raise(
        self, lst: ListEntity, syn: FieldSlotStr
    ) -> TaskEntity:
        tup = self._task_repo.get_by_list_id_and_syn(lst.list_id, syn)

        if tup is None:
            raise business.NotFoundBySyn(syn, TaskEntity)

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
