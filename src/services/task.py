import functools
import typing as t
from dataclasses import dataclass

from domain import errors
from domain.entities.attribute import AttributeEntity
from domain.entities.community import CommunityEntity
from domain.entities.list import ListEntity
from domain.entities.member import MemberEntity
from domain.entities.task import TaskEntity
from domain.enums.attribute import AttributeKind, AttributeSlotType, AttributeType
from domain.enums.edit_mode import AliasEditMode, FieldMappingEditMode
from domain.enums.rank import CommunityRank
from domain.sentinels.default import DEFAULT
from domain.types.attribute import AttributeID
from domain.types.collection_entry import CollectionT
from domain.types.field_mapping import EntityFrozenFieldMappingT, RawFieldMappingT
from domain.types.task import TaskID
from domain.value_objects.attribute import AttributeSynStr
from domain.value_objects.community import CommunityNameStr
from domain.value_objects.field_slot import FieldSlotStr
from domain.value_objects.index import Index
from domain.value_objects.list import ListNameStr
from repositories.attribute import AttributeRepository
from repositories.collection_entry import (
    CollectionEntryRepository,
)
from repositories.dtos.task import TaskAliasInsert, TaskInsert
from repositories.field_slot import FieldSlotInsert, FieldSlotRepository
from repositories.task import TaskRepository
from services.contexts.interacting_user import InteractingUserContext
from services.dtos.task import DeletedTask, TaskInfo
from services.internal.edit_mode import EditModeService
from services.internal.field_mapping import FieldMappingService
from services.list import ListAccessService
from services.internal.permission import PermissionService
from services.internal.slot_type import SlotTypeService


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
            raise errors.CountLimitReached(
                community.limits.list_task_count_max, TaskEntity
            )

        syns: tuple[FieldSlotStr, ...] = (task_name, *aliases)

        if len(aliases) > community.limits.field_slot_count_max:
            raise errors.AliasCountLimitReached(
                community.limits.field_slot_count_max, task_name, tuple(aliases)
            )

        # --- Verify Syn Uniquness Across Each Other And Across All Tasks --- #
        FieldSlotStr.raise_if_not_unique(syns)

        existing_same_syn = self._task_repo.get_first_by_list_id_and_any_syn(
            lst.list_id, syns, None
        )

        if existing_same_syn is not None:
            colliding_task, colliding_syn = existing_same_syn

            raise errors.SynAlreadyTaken(
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

    def delete(self, task_name: FieldSlotStr, list_name: ListNameStr) -> DeletedTask:
        _, member, lst, task = self._task_access_service.get_convenient(
            DEFAULT, list_name, task_name, True
        )

        self._permission_service.ensure_community_rank(member, CommunityRank.MODERATOR)

        self._task_repo.delete(task.task_id)

        return DeletedTask(task.name, lst)

    def edit_name(
        self, new_name: FieldSlotStr, task_name: FieldSlotStr, list_name: ListNameStr
    ) -> FieldSlotStr:
        _, member, lst, task = self._task_access_service.get_convenient(
            DEFAULT, list_name, task_name, True
        )

        self._permission_service.ensure_community_rank(member, CommunityRank.MODERATOR)

        # Exactly equal (real matches, not just norm)
        if task.name.real == new_name.real:
            raise errors.NameNotDifferent(task_name)

        existing_task_and_syn = self._task_repo.get_by_list_id_and_syn(
            lst.list_id,
            new_name,
        )

        if existing_task_and_syn is not None:
            existing_task, existing_syn = existing_task_and_syn

            # False if the current task has the same name but with different casing
            if not (existing_task == task and task.name == existing_syn):
                raise errors.SynAlreadyTaken(
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

        new_aliases = self._edit_mode_service.handle_alias_edit(edit_mode, current_aliases, new_aliases)

        # If aliases exactly equal to existing ones (including order even tho technically unimportant)
        if FieldSlotStr.sequences_requal(current_aliases, new_aliases):
            raise errors.AliasesNotDifferent(new_aliases)

        del current_aliases

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

            raise errors.SynAlreadyTaken(
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
    ) -> EntityFrozenFieldMappingT[AttributeType.TaskT]:
        _, member, lst, task = self._task_access_service.get_convenient(DEFAULT, list_name, task_name, True)

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

        new_fm = self._field_mapping_service.build_edit(edit_mode, self._field_slot_repo.get_field_mapping_by_task_id(task.task_id, ATTRIBUTE_TYPES), new_field_mapping, syn_to_attr, attr_id_to_collection)

        self._field_slot_repo.replace_all_by_task_id(task.task_id, (FieldSlotInsert(task.task_id, attr.attribute_id, Index(i), slot) for attr, field in new_fm.items() for i, slot in enumerate(field)))
        
        return new_fm


@dataclass(frozen=True, slots=True, eq=False)
class TaskQueryService:
    _task_access_service: TaskAccessService
    _task_repo: TaskRepository
    _attribute_repo: AttributeRepository
    _field_slot_repo: FieldSlotRepository
    _list_access_service: ListAccessService
    _collection_entry_repo: CollectionEntryRepository
    _slot_type_service: SlotTypeService

    def get_info(self, syn: FieldSlotStr, list_name: ListNameStr | DEFAULT) -> TaskInfo:
        _, _, lst, task = self._task_access_service.get_convenient(
            DEFAULT, list_name, syn, False
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
            frozendict(
                {
                    id_to_attr[k]: v
                    for k, v in field_mapping.items()
                }  # pyright: ignore[reportCallIssue]  Pyright bug for beta 3.15
            ),
            static_attributes,
        )

    def get_summaries(
        self,
        sorts: tuple[tuple[AttributeSynStr, bool], ...],
        list_name: ListNameStr | DEFAULT,
    ) -> tuple[tuple[tuple[FieldSlotStr, ...], ...], ...]:
        _, _, lst = self._list_access_service.get_convenient(DEFAULT, list_name)

        tasks: tuple[TaskEntity, ...] = self._task_repo.get_all_by_list_id(lst.list_id)

        ATTRIBUTES_TYPES: t.Final = AttributeType.NON_USER()

        SYN_TO_ATTR: t.Final = self._attribute_repo.get_syn_to_attribute_by_list_id(
            lst.list_id, ATTRIBUTES_TYPES
        )
        ATTRS_SORTED: t.Final = tuple(
            sorted(set(SYN_TO_ATTR.values()), key=lambda attr: attr.position.value)
        )

        TASK_ID_TO_STATIC_FIELD_MAPPING: t.Final[dict[
            TaskID, dict[AttributeID, tuple[FieldSlotStr, ...]]
        ]] = {}
        TASK_ID_TO_ALIASES: t.Final = self._task_repo.get_grouped_aliases_by_list_id(lst.list_id)

        for attr in ATTRS_SORTED:
            if attr.type is not AttributeType.STATIC:
                continue

            match attr.kind:
                case AttributeKind.ID:
                    for task in tasks:
                        TASK_ID_TO_STATIC_FIELD_MAPPING.setdefault(task.task_id, {})[
                            attr.attribute_id
                        ] = (FieldSlotStr(str(task.task_id)),)

                case AttributeKind.NAME:
                    for task in tasks:
                        TASK_ID_TO_STATIC_FIELD_MAPPING.setdefault(task.task_id, {})[
                            attr.attribute_id
                        ] = (task.name,)

                case AttributeKind.ALIAS:
                    for task in tasks:
                        TASK_ID_TO_STATIC_FIELD_MAPPING.setdefault(task.task_id, {})[
                            attr.attribute_id
                        ] = TASK_ID_TO_ALIASES.get(task.task_id, ())

                case _:
                    assert attr.kind is not AttributeKind.NONE
                    t.assert_never(attr.kind)

        TASK_ID_TO_TASK_FIELD_MAPPING: t.Final = {
            task_id: {
                attr_id: field
                for attr_id, field in mapping.items()
            }
            for task_id, mapping in self._field_slot_repo.get_task_field_mapping_by_list_id(
                lst.list_id
            ).items()
        }

        TASK_ID_TO_FIELD_MAPPING: t.Final = {
            task.task_id: TASK_ID_TO_STATIC_FIELD_MAPPING.get(task.task_id, {})
            | TASK_ID_TO_TASK_FIELD_MAPPING.get(task.task_id, {})
            for task in tasks
        }

        del TASK_ID_TO_STATIC_FIELD_MAPPING, TASK_ID_TO_TASK_FIELD_MAPPING

        attr_id_to_collection = (
            self._collection_entry_repo.get_grouped_collections_by_list_id(
                lst.list_id, AttributeType.TASK.as_set()
            )
        )

        tasks = tuple(
            self._sort(
                sorts,
                tasks,
                TASK_ID_TO_FIELD_MAPPING,
                SYN_TO_ATTR,
                attr_id_to_collection,
            )
        )

        return tuple(
            tuple(TASK_ID_TO_FIELD_MAPPING[task.task_id].get(attr.attribute_id, ()) for attr in ATTRS_SORTED)
            for task in tasks
        )

    def _sort[T: AttributeType](
        self,
        sorts: t.Sequence[tuple[AttributeSynStr, bool]],
        tasks: t.Sequence[TaskEntity],
        task_id_to_field_mapping: t.Mapping[
            TaskID, t.Mapping[AttributeID, tuple[FieldSlotStr, ...]]
        ],
        syn_to_attr: t.Mapping[AttributeSynStr, AttributeEntity[T]],
        attr_id_to_collection: t.Mapping[
            AttributeID, CollectionT
        ],
    ) -> list[TaskEntity]:
        # --- Normalize Sorts As Much As Possible --- #
        optimized_sorts: list[tuple[AttributeEntity[T], bool]] = []
        seen: set[AttributeEntity[T]] = set()

        for sort in sorts:
            syn, asc = sort
            attr = syn_to_attr[syn]

            # Remove duplicate attrs because unnecessary
            if attr in seen:
                continue

            seen.add(attr)

            optimized_sorts.append((attr, asc))

            # Short circuit when we know last sort results in unique data
            if attr.slot_unique_across_list:
                break

        del sorts
        
        if not optimized_sorts:
            name_attr: AttributeEntity.OfTypeStaticT

            for attr in syn_to_attr.values():
                if attr.kind is AttributeKind.NAME:
                    name_attr = attr  # type: ignore
                    break
            else:
                raise ValueError("Data error, no name attribute found!!!")

            optimized_sorts = [(name_attr, True)]  # type: ignore

        # --- Gather Sorting Data --- #
        task_to_sort_value: dict[TaskEntity, list[tuple[AttributeSlotType.SlotTypeT, ...]]] = {}

        # TODO: Could be optimized to only fetch collection entry values excluding aliases 
        attr_id_to_collection_value_to_collection_index: dict[
            AttributeID, dict[FieldSlotStr, int]
        ] = {
            attr: {
                entry_with_aliases[0]: i
                for i, entry_with_aliases in enumerate(coll)
            }
            for attr, coll in attr_id_to_collection.items()
        }

        for task in tasks:
            result: list[tuple[AttributeSlotType.SlotTypeT, ...]] = []

            for attr, _ in optimized_sorts:
                syn_to_collection_entry_idx = (
                    attr_id_to_collection_value_to_collection_index.get(
                        attr.attribute_id, {}
                    )
                )

                # Collection exists for given attr
                if syn_to_collection_entry_idx:
                    # It is possible that a slot does not match any collection value in case that
                    # a user attribute's collection is edited and staff did not yet fix the users'
                    # data.
                    result.append(
                        tuple(
                            syn_to_collection_entry_idx.get(slot, -1)
                            for slot in task_id_to_field_mapping.get(
                                task.task_id, {}
                            ).get(attr.attribute_id, ())
                        )
                    )
                else:
                    result.append(
                        tuple(
                            self._slot_type_service.convert_to_type(
                                slot, attr.slot.type, _validate=False
                            )
                            for slot in task_id_to_field_mapping.get(
                                task.task_id, {}
                            ).get(attr.attribute_id, ())
                        )
                    )

            task_to_sort_value[task] = result

        # --- Apply Sort --- #
        def compare_tasks(a: TaskEntity, b: TaskEntity) -> int:
            values_a = task_to_sort_value[a]
            values_b = task_to_sort_value[b]

            for va, vb, (_, asc) in zip(values_a, values_b, optimized_sorts):
                if va < vb:
                    return -1 if asc else 1

                if va > vb:
                    return 1 if asc else -1

            return 0

        return sorted(tasks, key=functools.cmp_to_key(compare_tasks))


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
