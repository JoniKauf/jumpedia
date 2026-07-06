import typing as t
from dataclasses import dataclass

from domain import errors
from domain.entities.community import CommunityEntity
from domain.entities.list import ListEntity
from domain.entities.member import MemberEntity
from domain.entities.member_task import MemberTaskEntity
from domain.entities.task import TaskEntity
from domain.enums.attribute import AttributeType
from domain.sentinels.default import DEFAULT
from domain.types.member import MemberID
from domain.types.task import TaskID
from domain.value_objects.field_slot import FieldSlotStr
from domain.value_objects.index import Index
from domain.value_objects.list import ListNameStr
from repositories.attribute import AttributeRepository, AttributeSynStr
from repositories.collection_entry import CollectionEntryRepository
from repositories.community import CommunityNameStr
from repositories.dtos.member_field_slot import MemberFieldSlotInsert
from repositories.dtos.member_task import MemberTaskInsert
from repositories.field_slot import FieldSlotRepository
from repositories.member_field_slot import MemberFieldSlotRepository
from repositories.member_task import MemberTaskRepository
from repositories.task import TaskRepository
from services.community import PermissionService
from services.contexts.interacting_user import InteractingUserContext
from services.dtos.user import UserRef
from services.field_mapping import FieldMappingService
from services.list import ListAccessService
from services.member import MemberAccessService, MemberExistenceService
from services.task import TaskAccessService
from services.user import UserExistenceService


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
        user_field_mapping: t.Mapping[AttributeSynStr, tuple[FieldSlotStr, ...]],
        target_user: UserRef | DEFAULT,
    ) -> tuple[MemberEntity, TaskEntity]:
        _, actor_member, lst, task = self._task_access_service.get_convenient(
            DEFAULT, list_name, syn, False
        )

        target_member = self._member_access_service.get_target_member_if_actor_member_is_permitted_to_act_for_others(
            actor_member, target_user
        )

        del actor_member

        existing_member_task = self._member_task_repo.get_by_member_id_and_task_id(
            target_member.member_id, task.task_id
        )

        if existing_member_task is not None:
            raise errors.MemberAlreadyHasTask(target_member, task)

        ATTRIBUTE_TYPES: t.Final = AttributeType.USER.as_set()

        syn_to_attr = self._attribute_repo.get_syn_to_attribute_by_list_id(
            lst.list_id, ATTRIBUTE_TYPES
        )
        attr_id_to_collection = (
            self._collection_entry_repo.get_grouped_collections_by_list_id(
                lst.list_id, ATTRIBUTE_TYPES
            )
        )

        ufm = self._field_mapping_service.validate_and_build(
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
        syn: FieldSlotStr,
        list_name: ListNameStr | DEFAULT,
        target_user: UserRef | DEFAULT,
    ) -> tuple[MemberEntity, TaskEntity]:
        _, actor_member, _, task = self._task_access_service.get_convenient(
            DEFAULT, list_name, syn, False
        )

        target_member = self._member_access_service.get_target_member_if_actor_member_is_permitted_to_act_for_others(
            actor_member, target_user
        )

        del actor_member

        existing_target_member = self._member_task_repo.get_by_member_id_and_task_id(
            target_member.member_id, task.task_id
        )

        if existing_target_member is None:
            raise errors.MemberDoesNotHaveTask(target_member)

        self._member_task_repo.delete(existing_target_member.member_task_id)

        return target_member, task


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
