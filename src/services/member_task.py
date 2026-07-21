import typing as t
from dataclasses import dataclass

from domain.entities.attribute import AttributeEntity
from domain.entities.community import CommunityEntity
from domain.entities.list import ListEntity
from domain.entities.member import MemberEntity
from domain.entities.member_task import MemberTaskEntity
from domain.entities.task import TaskEntity
from domain.enums.attribute import AttributeKind, AttributeType
from domain.enums.edit_mode import FieldMappingEditMode
from domain.errors import business
from domain.sentinels.default import DEFAULT
from domain.typing.attribute import AnyAttributeTypeT, SlotTypeT, TaskAttributeTypeT
from domain.typing.community import CommunityID
from domain.typing.field_mapping import (
    FrozenFieldMappingEntityToStrings,
    RawFieldMappingT,
)
from domain.typing.member import MemberID
from domain.typing.task import TaskID
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
from repositories.member import MemberRepository
from repositories.member_field_slot import MemberFieldSlotRepository
from repositories.member_task import MemberTaskRepository
from repositories.task import TaskRepository
from services.community import ListAccessService
from services.contexts.interacting_user import InteractingUserContext
from services.dtos.user import UserRef
from services.internal.field_mapping import (
    FieldMappingBuildService,
    FieldMappingExtractionService,
    FieldMappingService,
    FieldMappingTransformationService,
)
from services.internal.slot_type import SlotTypeService
from services.member import MemberAccessService, MemberExistenceService, MemberService
from services.task import TaskAccessService


@dataclass(frozen=True, slots=True, eq=False)
class MemberTaskService:
    _attribute_repo: AttributeRepository
    _field_mapping_service: FieldMappingBuildService
    _collection_entry_repo: CollectionEntryRepository
    _task_access_service: TaskAccessService
    _member_access_service: MemberAccessService
    _member_task_repo: MemberTaskRepository
    _member_field_slot_repo: MemberFieldSlotRepository

    def give_to_user(
        self,
        syn: FieldSlotStr,
        list_name: ListNameStr | DEFAULT,
        user_field_mapping: RawFieldMappingT,
        target_user: UserRef | DEFAULT,
    ) -> tuple[MemberEntity, TaskEntity]:
        _, actor_member, lst, task = self._task_access_service.get_convenient(
            DEFAULT, list_name, syn, False
        )

        target_member = self._member_access_service.get_target_member_if_actor_member_is_permitted_to_act_for_others(
            actor_member, target_user
        )

        given_by_id = actor_member.member_id

        del actor_member, target_user

        existing_member_task = self._member_task_repo.get_by_member_id_and_task_id(
            target_member.member_id, task.task_id
        )

        if existing_member_task is not None:
            raise business.MemberAlreadyHasTask(target_member, task)

        ATTRIBUTE_TYPES: t.Final = AttributeType.USER.as_set()
        ATTRIBUTE_KINDS: t.Final = AttributeKind.NONE_KINDED

        syn_to_attr = self._attribute_repo.get_syn_to_attribute_by_list_id(
            lst.list_id, ATTRIBUTE_TYPES, ATTRIBUTE_KINDS
        )
        attr_id_to_collection = (
            self._collection_entry_repo.get_grouped_collections_by_list_id(
                lst.list_id, ATTRIBUTE_TYPES, ATTRIBUTE_KINDS
            )
        )

        ufm = self._field_mapping_service.build_raw(
            user_field_mapping, syn_to_attr, attr_id_to_collection
        )

        member_task = self._member_task_repo.create(
            MemberTaskInsert(target_member.member_id, task.task_id, given_by_id)
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
        new_member_field_mapping: RawFieldMappingT,
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
        ATTRIBUTE_KINDS: t.Final = AttributeKind.NONE_KINDED

        syn_to_attr = self._attribute_repo.get_syn_to_attribute_by_list_id(
            lst.list_id, ATTRIBUTE_TYPES, ATTRIBUTE_KINDS
        )
        attr_id_to_collection = (
            self._collection_entry_repo.get_grouped_collections_by_list_id(
                lst.list_id, ATTRIBUTE_TYPES, ATTRIBUTE_KINDS
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
    _task_repo: TaskRepository
    _attribute_repo: AttributeRepository
    _field_slot_repo: FieldSlotRepository
    _list_access_service: ListAccessService
    _collection_entry_repo: CollectionEntryRepository
    _member_field_slot_repo: MemberFieldSlotRepository
    _member_existence_service: MemberExistenceService
    _slot_type_service: SlotTypeService
    _member_task_access_service: MemberTaskAccessService
    _member_repo: MemberRepository
    _member_task_repo: MemberTaskRepository
    _field_mapping_transformation_service: FieldMappingTransformationService
    _field_mapping_extraction_service: FieldMappingExtractionService
    _field_mapping_service: FieldMappingService

    def get_info(
        self,
        syn: FieldSlotStr,
        target_user: UserRef | DEFAULT,
        list_name: ListNameStr | DEFAULT,
    ) -> FrozenFieldMappingEntityToStrings[AnyAttributeTypeT]:
        return self._field_mapping_service.get_info(syn, list_name, target_user)

    def get_summaries(
        self,
        filter: FilterT | None,
        sort: t.Sequence[tuple[AttributeSynStr, bool]],
        yield_: t.Sequence[AttributeSynStr],
        target_user: UserRef | DEFAULT,
        list_name: ListNameStr | DEFAULT,
    ) -> frozendict[
        AttributeEntity[AnyAttributeTypeT],
        tuple[tuple[SlotTypeT, ...], ...],
    ]:
        return self._field_mapping_service.get_summaries(
            filter, sort, yield_, list_name, target_user, False
        )

    def get_summaries_missing(
        self,
        filter: FilterT | None,
        sort: t.Sequence[tuple[AttributeSynStr, bool]],
        yield_: t.Sequence[AttributeSynStr],
        target_user: UserRef | DEFAULT,
        list_name: ListNameStr | DEFAULT,
    ) -> frozendict[
        AttributeEntity[TaskAttributeTypeT],
        tuple[tuple[SlotTypeT, ...], ...],
    ]:
        return self._field_mapping_service.get_summaries(
            filter, sort, yield_, list_name, target_user, True
        )


@dataclass(frozen=True, slots=True, eq=False)
class MemberTaskAccessService:
    _ctx: InteractingUserContext
    _member_task_repo: MemberTaskRepository
    _task_access_service: TaskAccessService
    _member_existence_service: MemberExistenceService

    def get_member_task_or_raise(
        self, target_user: UserRef | DEFAULT, community_id: CommunityID, task_id: TaskID
    ) -> tuple[MemberEntity, MemberTaskEntity]:
        target_member = self._member_existence_service.get_or_create_with_user_ref(
            target_user, community_id
        )
        member_task = self._member_task_repo.get_by_member_id_and_task_id(
            target_member.member_id, task_id
        )

        if member_task is None:
            raise ValueError("member doesn't have task")

        return target_member, member_task

    def get_convenient(
        self,
        community_name: CommunityNameStr | DEFAULT,
        list_name: ListNameStr | DEFAULT,
        task_syn: FieldSlotStr,
        task_only_by_name: bool,
        target_user: UserRef | DEFAULT,
    ) -> tuple[
        CommunityEntity,
        MemberEntity,
        ListEntity,
        TaskEntity,
        MemberEntity,
        MemberTaskEntity,
    ]:
        community, member, lst, task = self._task_access_service.get_convenient(
            community_name, list_name, task_syn, task_only_by_name
        )

        return (community, member, lst, task) + (
            self.get_member_task_or_raise(
                target_user, community.community_id, task.task_id
            )
        )
