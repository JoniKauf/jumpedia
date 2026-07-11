import typing as t
from dataclasses import dataclass

from domain.entities.attribute import AttributeEntity
from domain.entities.community import CommunityEntity
from domain.entities.list import ListEntity
from domain.entities.member import MemberEntity
from domain.entities.member_task import MemberTaskEntity
from domain.entities.task import TaskEntity
from domain.enums.attribute import AttributeType
from domain.enums.edit_mode import FieldMappingEditMode
from domain.errors import business
from domain.sentinels.default import DEFAULT
from domain.types.field_mapping import FieldMappingEntityFrozenT, FieldMappingRawT
from domain.types.member import MemberID
from domain.value_objects.field_slot import FieldSlotStr
from domain.value_objects.filter import FilterT
from domain.value_objects.index import Index
from domain.value_objects.list import ListNameStr
from repositories.attribute import AttributeRepository, AttributeSynStr
from repositories.collection_entry import CollectionEntryRepository
from repositories.community import CommunityNameStr
from repositories.dtos.member import MemberInsert
from repositories.dtos.member_field_slot import MemberFieldSlotInsert
from repositories.dtos.member_task import MemberTaskInsert
from repositories.field_slot import FieldSlotRepository
from repositories.member_field_slot import MemberFieldSlotRepository
from repositories.member_task import MemberTaskRepository
from repositories.task import TaskRepository
from services.community import ListAccessService
from services.contexts.interacting_user import InteractingUserContext
from services.dtos.user import UserRef
from services.internal.field_mapping import FieldMappingService
from services.member import MemberAccessService, MemberExistenceService, MemberService
from services.task import TaskAccessService


@dataclass(frozen=True, slots=True, eq=False)
class MemberTaskService:
    _attribute_repo: AttributeRepository
    _field_mapping_service: FieldMappingService
    _collection_entry_repo: CollectionEntryRepository
    _task_access_service: TaskAccessService
    _member_access_service: MemberAccessService
    _member_task_repo: MemberTaskRepository
    _member_field_slot_repo: MemberFieldSlotRepository

    def give_to_user(
        self,
        syn: FieldSlotStr,
        list_name: ListNameStr | DEFAULT,
        user_field_mapping: FieldMappingRawT,
        target_user: UserRef | DEFAULT,
    ) -> tuple[MemberEntity, TaskEntity]:
        _, actor_member, lst, task = self._task_access_service.get_convenient(
            DEFAULT, list_name, syn, False
        )

        target_member = self._member_access_service.get_target_member_if_actor_member_is_permitted_to_act_for_others(
            actor_member, target_user
        )

        del actor_member, target_user

        existing_member_task = self._member_task_repo.get_by_member_id_and_task_id(
            target_member.member_id, task.task_id
        )

        if existing_member_task is not None:
            raise business.MemberAlreadyHasTask(target_member, task)

        ATTRIBUTE_TYPES: t.Final = AttributeType.USER.as_set()

        syn_to_attr = self._attribute_repo.get_syn_to_attribute_by_list_id(
            lst.list_id, ATTRIBUTE_TYPES
        )
        attr_id_to_collection = (
            self._collection_entry_repo.get_grouped_collections_by_list_id(
                lst.list_id, ATTRIBUTE_TYPES
            )
        )

        ufm = self._field_mapping_service.build_raw(
            user_field_mapping, syn_to_attr, attr_id_to_collection
        )

        member_task = self._member_task_repo.create(
            MemberTaskInsert(target_member.member_id, task.task_id)
        )

        if ufm:
            inserts: list[MemberFieldSlotInsert] = []

            for attr, field in ufm.items():
                for i, slot in enumerate(field):
                    inserts.append(
                        MemberFieldSlotInsert(
                            member_task.member_task_id,
                            attr.attribute_id,
                            Index(i),
                            slot,
                        )
                    )

            if inserts:
                self._member_field_slot_repo.create_many(inserts)

        return target_member, task

    def take_from_user(
        self,
        task_syn: FieldSlotStr,
        list_name: ListNameStr | DEFAULT,
        target_user: UserRef | DEFAULT,
    ) -> tuple[MemberEntity, TaskEntity]:
        _, actor_member, _, task = self._task_access_service.get_convenient(
            DEFAULT, list_name, task_syn, False
        )

        target_member = self._member_access_service.get_target_member_if_actor_member_is_permitted_to_act_for_others(
            actor_member, target_user
        )

        del actor_member, target_user

        existing_target_member = self._member_task_repo.get_by_member_id_and_task_id(
            target_member.member_id, task.task_id
        )

        if existing_target_member is None:
            raise business.MemberDoesNotHaveTask(target_member)

        self._member_task_repo.delete(existing_target_member.member_task_id)

        return target_member, task

    def edit_member_field_mapping(
        self,
        new_member_field_mapping: FieldMappingRawT,
        edit_mode: FieldMappingEditMode,
        target_user: UserRef | DEFAULT,
        task_syn: FieldSlotStr,
        list_name: ListNameStr | DEFAULT,
    ) -> tuple[MemberEntity, TaskEntity]:
        _, actor_member, lst, task = self._task_access_service.get_convenient(
            DEFAULT, list_name, task_syn, False
        )

        target_member = self._member_access_service.get_target_member_if_actor_member_is_permitted_to_act_for_others(
            actor_member, target_user
        )

        del actor_member, target_user

        member_task = self._member_task_repo.get_by_member_id_and_task_id(
            target_member.member_id, task.task_id
        )

        if member_task is None:
            raise business.MemberDoesNotHaveTask(target_member)

        ATTRIBUTE_TYPES: t.Final = AttributeType.USER.as_set()

        syn_to_attr = self._attribute_repo.get_syn_to_attribute_by_list_id(
            lst.list_id, ATTRIBUTE_TYPES
        )
        attr_id_to_collection = (
            self._collection_entry_repo.get_grouped_collections_by_list_id(
                lst.list_id, ATTRIBUTE_TYPES
            )
        )

        new_mfm = self._field_mapping_service.build_edit(
            edit_mode,
            self._member_field_slot_repo.get_field_mapping_by_member_id_and_task_id(
                target_member.member_id, task.task_id
            ),
            new_member_field_mapping,
            syn_to_attr,
            attr_id_to_collection,
        )

        del new_member_field_mapping

        self._member_field_slot_repo.replace_all_by_member_task_id(
            member_task.member_task_id,
            (
                MemberFieldSlotInsert(
                    member_task.member_task_id, attr.attribute_id, Index(i), slot
                )
                for attr, field in new_mfm.items()
                for i, slot in enumerate(field)
            ),
        )

        return target_member, task


@dataclass(frozen=True, slots=True, eq=False)
class MemberTaskQueryService:
    _task_access_service: TaskAccessService
    _task_repo: TaskRepository
    _attribute_repo: AttributeRepository
    _field_slot_repo: FieldSlotRepository
    _list_access_service: ListAccessService
    _collection_entry_repo: CollectionEntryRepository
    _field_mapping_service: FieldMappingService
    _member_field_slot_repo: MemberFieldSlotRepository
    _member_existence_service: MemberExistenceService

    def get_info(
        self,
        syn: FieldSlotStr,
        target_user: UserRef | DEFAULT,
        list_name: ListNameStr | DEFAULT,
    ) -> FieldMappingEntityFrozenT[AttributeType.AllT]:
        community, _, lst, task = self._task_access_service.get_convenient(
            DEFAULT, list_name, syn, False
        )

        target_member = self._member_existence_service.get_or_create_with_user_ref(
            target_user, community.community_id
        )

        del target_user

        ATTRIBUTE_TYPES: t.Final = AttributeType.ALL()

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

        user_field_mapping = (
            self._member_field_slot_repo.get_field_mapping_by_member_id_and_task_id(
                target_member.member_id, task.task_id
            )
        )

        field_mapping = static_field_mapping | task_field_mapping | user_field_mapping

        del static_field_mapping, task_field_mapping, user_field_mapping

        return frozendict(
            (attr, field_mapping.get(attr.attribute_id, ())) for attr in attrs
        )

    def get_summaries(
        self,
        filter: FilterT | None,
        sorts: tuple[tuple[AttributeSynStr, bool], ...],
        target_user: UserRef | DEFAULT,
        list_name: ListNameStr | DEFAULT,
    ) -> frozendict[
        AttributeEntity[AttributeType.AllT],
        tuple[tuple[FieldSlotStr, ...], ...],
    ]:
        community, _, lst = self._list_access_service.get_convenient(DEFAULT, list_name)

        target_member = self._member_existence_service.get_or_create_with_user_ref(
            target_user, community.community_id
        )

        del target_user

        ATTRIBUTES_TYPES: t.Final = AttributeType.ALL()

        syn_to_attr = self._attribute_repo.get_syn_to_attribute_by_list_id(
            lst.list_id, ATTRIBUTES_TYPES
        )
        attrs_sorted = tuple(
            sorted(set(syn_to_attr.values()), key=lambda attr: attr.position.value)
        )

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

        task_id_to_user_field_mapping = (
            self._member_field_slot_repo.get_grouped_field_mapping_by_member_id(
                target_member.member_id
            )
        )

        # Combine all 3 mappings into the final one
        field_mappings = tuple(
            (
                frozendict(static_field_mapping)
                | task_id_to_task_field_mapping.get(task_id, frozendict())
                | task_id_to_user_field_mapping.get(task_id, frozendict())
            )
            for task_id, static_field_mapping in task_id_to_static_field_mapping.items()
        )

        del task_id_to_static_field_mapping, task_id_to_task_field_mapping

        attr_id_to_collection = (
            self._collection_entry_repo.get_grouped_collections_by_list_id(
                lst.list_id, AttributeType.TASK.as_set()
            )
        )

        field_mappings = self._field_mapping_service.filter(
            filter,
            field_mappings,
            syn_to_attr,
            attr_id_to_collection
        )
        
        field_mappings = self._field_mapping_service.sort(
            sorts,
            field_mappings,
            syn_to_attr,
            attr_id_to_collection,
        )

        return frozendict(
            (
                attr,
                tuple(
                    field_mapping[attr.attribute_id] for field_mapping in field_mappings
                ),
            )
            for attr in attrs_sorted
        )


@dataclass(frozen=True, slots=True, eq=False)
class MemberTaskAccessService:
    _ctx: InteractingUserContext
    _member_task_repo: MemberTaskRepository
    _task_access_service: TaskAccessService

    def get_convenient(
        self,
        community_name: CommunityNameStr | DEFAULT,
        list_name: ListNameStr | DEFAULT,
        task_syn: FieldSlotStr,
        task_only_by_name: bool,
        target_member_id: MemberID | DEFAULT,
    ) -> tuple[
        CommunityEntity, MemberEntity, ListEntity, TaskEntity, MemberTaskEntity | None
    ]:
        community, member, lst, task = self._task_access_service.get_convenient(
            community_name, list_name, task_syn, task_only_by_name
        )

        member_task = self._member_task_repo.get_by_member_id_and_task_id(
            member.member_id if target_member_id is DEFAULT else target_member_id,
            task.task_id,
        )

        return (community, member, lst, task, member_task)
