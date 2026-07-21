import typing as t
from dataclasses import dataclass

from domain.entities.attribute import AttributeEntity
from domain.entities.collection_entry import CollectionEntryEntity
from domain.entities.community import CommunityEntity
from domain.entities.list import ListEntity
from domain.entities.member import MemberEntity
from domain.entities.task import TaskEntity
from domain.enums.attribute import AttributeKind, AttributeSlotType, AttributeType
from domain.enums.edit_mode import AliasEditMode, CollectionEditMode
from domain.enums.rank import CommunityRank
from domain.errors import business
from domain.sentinels.default import DEFAULT
from domain.typing.attribute import (
    AnyAttributeTypeT,
    AttributeID,
    TaskAttributeTypeT,
    UserAttributeTypeT,
)
from domain.typing.collection_entry import CollectionFrozenT, CollectionT
from domain.value_objects.attribute import (
    AttributeFieldConfig,
    AttributeSynStr,
    KindedAttributeDefaultProperties,
)
from domain.value_objects.community import CommunityLimits, CommunityNameStr
from domain.value_objects.field_slot import FieldSlotStr
from domain.value_objects.index import Index
from domain.value_objects.list import ListNameStr
from domain.value_objects.position import Position
from repositories.attribute import AttributeRepository
from repositories.collection_entry import CollectionEntryRepository
from repositories.dtos.attribute import AttributeAliasInsert, AttributeInsert
from repositories.dtos.field_slot import FieldSlotInsert
from repositories.field_slot import FieldSlotRepository
from services.community import CommunityAccessService
from services.contexts.interacting_user import InteractingUserContext
from services.dtos.attribute import (
    AttributeInfo,
    AttributeSummary,
    PreparedDeleteAttribute,
)
from services.internal.edit_mode import EditModeService
from services.internal.permission import PermissionService
from services.list import ListAccessService
from services.member import MemberAccessService


@dataclass(frozen=True, slots=True, eq=False)
class AttributeService:
    _attribute_repo: AttributeRepository
    _collection_entry_repo: CollectionEntryRepository
    _permission_service: PermissionService
    _list_access_service: ListAccessService
    _attribute_access_service: AttributeAccessService
    _field_slot_repo: FieldSlotRepository
    _edit_mode_service: EditModeService

    def create[T: TaskAttributeTypeT | UserAttributeTypeT](
        self,
        name: AttributeSynStr,
        list_name: ListNameStr,
        type: T,
        slot: AttributeFieldConfig,
        aliases: tuple[AttributeSynStr, ...],
        collection: CollectionT,
    ) -> AttributeEntity[T]:
        community, member, lst = self._list_access_service.get_convenient(
            DEFAULT, list_name
        )

        self._permission_service.ensure_community_rank(
            member, CommunityRank.ADMINISTRATOR
        )

        attr_count = self._attribute_repo.count_by_list(lst.list_id)

        self._validate_basic_community_limits(name, aliases, community, attr_count)

        self._validate_syn_uniqueness(name, aliases, lst)

        self._validate_field_config(slot, community, True)

        self._validate_collection_community_limits(collection, community)

        self._validate_collection_syn_uniqueness(collection)

        # --- Create Attribute ---
        attr_entity = self._attribute_repo.create(
            AttributeInsert(
                lst.list_id,
                name,
                type,
                AttributeKind.NONE,
                slot,
                Position(attr_count + 1),
            )
        )

        # --- Create Attribute Aliases ---
        self._attribute_repo.create_many_aliases(
            AttributeAliasInsert(attr_entity.attribute_id, Index(i), lst.list_id, alias)
            for i, alias in enumerate(aliases)
        )

        # --- Create Attribute Collection ---
        self._collection_entry_repo.create_collection(
            attr_entity.attribute_id, collection
        )

        return attr_entity

    def delete(self, prepared: PreparedDeleteAttribute) -> None:
        self._attribute_repo.delete(prepared.attribute_id)
        self._attribute_repo.decrement_positions_after(
            prepared.list_id, prepared.attribute_position
        )

    def edit_name(
        self,
        current_name: AttributeSynStr,
        new_name: AttributeSynStr,
        list_name: ListNameStr,
    ) -> AttributeSynStr:
        _, member, lst, attr = self._attribute_access_service.get_convenient(
            DEFAULT, list_name, current_name, True
        )

        self._permission_service.ensure_community_rank(
            member, CommunityRank.ADMINISTRATOR
        )

        # Exactly equal (real matches, not just norm)
        if attr.name.real == new_name.real:
            raise business.NameNotDifferent(current_name)

        existing_attr_and_syn = self._attribute_repo.get_by_list_id_and_syn(
            lst.list_id,
            new_name,
        )

        if existing_attr_and_syn is not None:
            existing_attr, existing_syn = existing_attr_and_syn

            # False if the current attribute has the same name but with different casing
            if not (existing_attr == attr and attr.name == existing_syn):
                raise business.SynAlreadyTaken(
                    existing_attr, new_name, existing_attr.name != existing_syn, False
                )

        self._attribute_repo.update_name(attr.attribute_id, new_name)

        return attr.name

    def edit_aliases(
        self,
        name: AttributeSynStr,
        new_aliases: tuple[AttributeSynStr, ...],
        list_name: ListNameStr,
        edit_mode: AliasEditMode,
    ) -> AttributeEntity:
        community, member, lst, attr = self._attribute_access_service.get_convenient(
            DEFAULT, list_name, name, True
        )

        self._permission_service.ensure_community_rank(
            member, CommunityRank.ADMINISTRATOR
        )

        AttributeSynStr.raise_if_not_unique(new_aliases)

        current_aliases = self._attribute_repo.get_aliases_by_attribute_id(
            attr.attribute_id
        )

        new_aliases = self._edit_mode_service.handle_alias_edit(
            edit_mode, current_aliases, new_aliases
        )

        # If aliases exactly equal to existing ones (including order even tho technically unimportant)
        if AttributeSynStr.sequences_requal(current_aliases, new_aliases):
            raise business.AliasesNotDifferent(new_aliases)

        del current_aliases

        if len(new_aliases) > community.limits.attribute_alias_count_max:
            raise business.AliasCountLimitReached(
                community.limits.attribute_alias_count_max, attr.name, new_aliases
            )

        # Check if name collision with current attribute
        for alias in new_aliases:
            if alias == attr.name:
                raise business.SynAlreadyTaken(attr, alias, False, True)

        existing_attr_and_syn = self._attribute_repo.get_first_by_list_id_and_any_syn(
            lst.list_id, new_aliases, attr.attribute_id
        )

        # Check syn collision for other attributes (collisions with aliases of current attr are allowed)
        if existing_attr_and_syn is not None:
            existing_attr, existing_syn = existing_attr_and_syn

            raise business.SynAlreadyTaken(
                existing_attr, existing_syn, existing_attr.name != existing_syn, True
            )

        self._attribute_repo.update_aliases(
            attr.attribute_id,
            (
                AttributeAliasInsert(attr.attribute_id, Index(i), lst.list_id, alias)
                for i, alias in enumerate(new_aliases)
            ),
        )

        return attr

    def edit_min_and_max_slot_count(
        self,
        name: AttributeSynStr,
        list_name: ListNameStr,
        min_slot_count: int,
        max_slot_count: int,
    ) -> AttributeEntity:
        community, member, _, attr = self._attribute_access_service.get_convenient(
            DEFAULT, list_name, name, True
        )

        self._permission_service.ensure_community_rank(
            member, CommunityRank.ADMINISTRATOR
        )

        if attr.kind is not AttributeKind.NONE:
            raise ValueError("Cannot change slot count for static attributes")

        field_config = AttributeFieldConfig(
            attr.field_config.slot_type,
            min_slot_count,
            max_slot_count,
            attr.field_config.unique_slots,
        )

        del min_slot_count, max_slot_count

        self._validate_field_config(field_config, community, False)

        # Task fields are entirely in control for staff team. Enforce that all fields must fit first before allowing change.
        if attr.type is AttributeType.TASK:
            task_to_slots = self._field_slot_repo.get_grouped_by_task(attr.attribute_id)

            invalid_tasks: dict[TaskEntity, tuple[FieldSlotStr, ...]] = {}

            for task, slots in task_to_slots.items():
                if (
                    len(slots) < field_config.min_slot_count
                    or len(slots) > field_config.max_slot_count
                ):
                    invalid_tasks[task] = slots

            if invalid_tasks:
                raise business.TasksDoNotMatchMinOrMaxSlotCountCriteria(
                    field_config.min_slot_count,
                    field_config.max_slot_count,
                    invalid_tasks,
                )

        else:
            # Do not validate whether all users' field data fits the new criteria. This would be a disaster for the staff to deal with beforehand.
            # Keep it as a soft limit and staff can safely change it afterwards.
            t.assert_type(attr.type, UserAttributeTypeT)

        self._attribute_repo.update_min_and_max_slot_count(
            attr.attribute_id, field_config.min_slot_count, field_config.max_slot_count
        )

        attr.field_config = field_config

        return attr

    def edit_position_order(
        self, attribute_names: tuple[AttributeSynStr, ...], list_name: ListNameStr
    ) -> ListEntity:
        _, member, lst = self._list_access_service.get_convenient(DEFAULT, list_name)

        self._permission_service.ensure_community_rank(
            member, CommunityRank.ADMINISTRATOR
        )

        name_to_attr = {
            attr.name: attr
            for attr in self._attribute_repo.get_all_by_list_id_ordered_by_position(
                lst.list_id, AttributeType.ALL, AttributeKind.ALL
            )
        }
        new_order: list[AttributeEntity] = []
        seen: set[AttributeEntity] = set()

        for name in attribute_names:
            attr = name_to_attr[name]

            if attr in seen:
                raise ValueError("Attribute specified more than once")

            new_order.append(attr)
            seen.add(attr)

        assert len(new_order) <= len(name_to_attr)

        if len(new_order) < len(name_to_attr):
            raise ValueError("Missing attrs")

        self._attribute_repo.update_positions(
            lst.list_id, tuple(attr.attribute_id for attr in new_order)
        )

        return lst

    def edit_collection(
        self,
        name: AttributeSynStr,
        list_name: ListNameStr,
        new_collection: CollectionT,
        edit_mode: CollectionEditMode,
    ) -> AttributeEntity:
        community, member, _, attr = self._attribute_access_service.get_convenient(
            DEFAULT, list_name, name, True
        )

        self._permission_service.ensure_community_rank(
            member, CommunityRank.ADMINISTRATOR
        )

        if attr.kind is not AttributeKind.NONE:
            raise ValueError("Cannot change collection for static attributes")

        current_collection: CollectionFrozenT = (
            self._collection_entry_repo.get_collection_by_attribute_id(
                attr.attribute_id
            )
        )

        new_collection = self._edit_mode_service.handle_collection_edit(
            edit_mode, current_collection, new_collection
        )

        self._validate_collection_syn_uniqueness(new_collection)

        if FieldSlotStr.sequences_requal(
            tuple(v for v, _ in current_collection), tuple(v for v, _ in new_collection)
        ) and all(
            FieldSlotStr.sequences_requal(a, b)
            for (_, a), (_, b) in zip(current_collection, new_collection)
        ):
            raise business.CollectionNotDifferent(new_collection)

        del current_collection

        self._validate_collection_community_limits(new_collection, community)

        if attr.type is AttributeType.TASK:
            syn_to_collection_entry_value: dict[FieldSlotStr, FieldSlotStr] = {
                syn: entry[0]
                for entry in new_collection
                for syn in (entry[0], *entry[1])
            }
            task_to_slots = self._field_slot_repo.get_grouped_by_task(attr.attribute_id)

            task_to_only_invalid_slots: dict[TaskEntity, tuple[FieldSlotStr, ...]] = {}

            for task, slots in task_to_slots.items():
                only_invalid_slots: tuple[FieldSlotStr, ...] = tuple(
                    slot for slot in slots if slot not in syn_to_collection_entry_value
                )

                if only_invalid_slots:
                    task_to_only_invalid_slots[task] = only_invalid_slots

            if task_to_only_invalid_slots:
                raise ValueError()

            tasks_to_new_data: dict[TaskEntity, tuple[FieldSlotStr, ...]] = {
                task: tuple(syn_to_collection_entry_value[slot] for slot in slots)
                for task, slots in task_to_slots.items()
            }

            self._field_slot_repo.replace_all_by_attribute_id(
                attr.attribute_id,
                (
                    FieldSlotInsert(task.task_id, attr.attribute_id, Index(i), slot)
                    for task, slots in tasks_to_new_data.items()
                    for i, slot in enumerate(slots)
                ),
            )
        else:
            # Do not validate whether all users' field data fits the new criteria. This would be a disaster for the staff to deal with beforehand.
            # Keep it as a soft limitation and staff can safely change it afterwards because users can't change it back to a now invalid collection entry.
            t.assert_type(attr.type, UserAttributeTypeT)

        self._collection_entry_repo.replace_collection(
            attr.attribute_id, new_collection
        )

        return attr

    def _validate_field_config(
        self,
        field_config: AttributeFieldConfig,
        community: CommunityEntity,
        creating_attribute: bool,
    ) -> None:
        if creating_attribute and field_config.min_slot_count != 0:
            raise business.InitialSlotCountMustBeZero()

        # Check slot count max does not exceed community limit here, because in Slot itself we don't know the community's limit
        if field_config.max_slot_count > community.limits.field_slot_count_max:
            raise business.SlotCountDefinitionLimitExceeded(
                field_config.min_slot_count,
                field_config.max_slot_count,
                CommunityLimits.FIELD_MIN_MIN_SLOT_COUNT,
                CommunityLimits.FIELD_MIN_MAX_SLOT_COUNT,
                community.limits.field_slot_count_max,
            )

    def _validate_collection_syn_uniqueness(self, entire_collection: CollectionT):
        FieldSlotStr.raise_if_not_unique(
            syn for entry in entire_collection for syn in (entry[0], *entry[1])
        )

    def _validate_basic_community_limits(
        self,
        name: AttributeSynStr,
        all_aliases_of_attr: tuple[AttributeSynStr, ...],
        community: CommunityEntity,
        list_attr_count: int,
    ) -> None:
        if list_attr_count >= community.limits.list_attribute_count_max:
            raise business.CountLimitReached(
                community.limits.list_attribute_count_max, AttributeEntity
            )

        if len(all_aliases_of_attr) > community.limits.attribute_alias_count_max:
            raise business.AliasCountLimitReached(
                community.limits.attribute_alias_count_max, name, all_aliases_of_attr
            )

    def _validate_collection_community_limits(
        self, entire_collection: CollectionT, community: CommunityEntity
    ) -> None:
        if len(entire_collection) > community.limits.collection_entry_count_max:
            raise business.CountLimitReached(
                community.limits.collection_entry_count_max,
                CollectionEntryEntity,
            )

        for entry in entire_collection:
            if len(entry[1]) > community.limits.collection_entry_alias_count_max:
                raise business.AliasCountLimitReached(
                    community.limits.collection_entry_alias_count_max,
                    entry[0],
                    entry[1],
                )

    def _validate_syn_uniqueness(
        self,
        name: AttributeSynStr,
        all_aliases_of_attr: tuple[AttributeSynStr, ...],
        lst: ListEntity,
    ):
        syns: tuple[AttributeSynStr, ...] = (name, *all_aliases_of_attr)

        AttributeSynStr.raise_if_not_unique(syns)

        existing_same_syn = self._attribute_repo.get_first_by_list_id_and_any_syn(
            lst.list_id, syns, None
        )

        if existing_same_syn is not None:
            colliding_attr, colliding_syn = existing_same_syn

            raise business.SynAlreadyTaken(
                *existing_same_syn,
                colliding_attr.name != colliding_syn,
                colliding_syn != name,
            )


@dataclass(frozen=True, slots=True, eq=False)
class AttributePrepareService:
    _attribute_access_service: AttributeAccessService
    _permission_service: PermissionService

    def delete(
        self, name: AttributeSynStr, list_name: ListNameStr
    ) -> tuple[PreparedDeleteAttribute, ListEntity, AttributeEntity]:
        _, member, lst, attr = self._attribute_access_service.get_convenient(
            DEFAULT, list_name, name, True
        )

        self._permission_service.ensure_community_rank(
            member, CommunityRank.ADMINISTRATOR
        )

        if attr.kind is not AttributeKind.NONE:
            raise ValueError("Cannot delete attribute of type static")

        return (
            PreparedDeleteAttribute(lst.list_id, attr.attribute_id, attr.position),
            lst,
            attr,
        )


@dataclass(frozen=True, slots=True, eq=False)
class AttributeQueryService:
    _attribute_repo: AttributeRepository
    _collection_entry_repo: CollectionEntryRepository
    _community_access_service: CommunityAccessService
    _member_access_service: MemberAccessService
    _list_access_service: ListAccessService
    _attribute_access_service: AttributeAccessService

    def get_info(
        self, syn: AttributeSynStr, list_name: ListNameStr | DEFAULT
    ) -> AttributeInfo:
        _, _, lst, attr = self._attribute_access_service.get_convenient(
            DEFAULT, list_name, syn, False
        )

        aliases = self._attribute_repo.get_aliases_by_attribute_id(attr.attribute_id)
        collection = self._collection_entry_repo.get_collection_by_attribute_id(
            attr.attribute_id
        )

        return AttributeInfo(
            attr.name,
            aliases,
            lst,
            attr.type,
            attr.kind,
            attr.field_config,
            attr.position,
            collection,
        )

    def get_summaries(
        self,
        list_name: ListNameStr | DEFAULT,
    ) -> tuple[AttributeSummary, ...]:
        _, _, lst = self._list_access_service.get_convenient(DEFAULT, list_name)

        ATTRIBUTE_TYPES: t.Final = AttributeType.ALL
        ATTRIBUTE_KINDS: t.Final = AttributeKind.ALL

        attrs = self._attribute_repo.get_all_by_list_id_ordered_by_position(
            lst.list_id, ATTRIBUTE_TYPES, ATTRIBUTE_KINDS
        )

        attr_id_to_aliases = (
            self._attribute_repo.get_grouped_aliases_by_list_id_ordered_by_pos(
                lst.list_id, ATTRIBUTE_TYPES, ATTRIBUTE_KINDS
            )
        )
        attr_id_to_collection = (
            self._collection_entry_repo.get_grouped_collections_by_list_id(
                lst.list_id, ATTRIBUTE_TYPES, AttributeKind.NONE_KINDED
            )
        )

        return tuple(
            AttributeSummary(
                attr.name,
                attr_id_to_aliases[attr.attribute_id],
                lst,
                attr.type,
                attr.kind,
                attr.field_config,
                attr.position,
                attr_id_to_collection[attr.attribute_id],
            )
            for attr in attrs
        )


@dataclass(frozen=True, slots=True, eq=False)
class AttributeAccessService:
    _ctx: InteractingUserContext
    _repo: AttributeRepository
    _list_access_service: ListAccessService

    def get_by_list_and_name_or_raise(
        self, lst: ListEntity, name: AttributeSynStr
    ) -> AttributeEntity:
        attr = self._repo.get_by_list_id_and_name(lst.list_id, name)

        if attr is None:
            raise business.NotFoundByName(name, AttributeEntity)

        return attr

    def get_by_list_and_syn_or_raise(
        self, lst: ListEntity, syn: AttributeSynStr
    ) -> AttributeEntity:
        existing_attr_and_syn = self._repo.get_by_list_id_and_syn(lst.list_id, syn)

        if existing_attr_and_syn is None:
            raise business.NotFoundBySyn(syn, AttributeEntity)

        return existing_attr_and_syn[0]

    def get_convenient(
        self,
        community_name: CommunityNameStr | DEFAULT,
        list_name: ListNameStr | DEFAULT,
        attribute_syn: AttributeSynStr,
        attribute_only_by_name: bool,
    ) -> tuple[CommunityEntity, MemberEntity, ListEntity, AttributeEntity]:
        community, member, lst = self._list_access_service.get_convenient(
            community_name, list_name
        )
        attr = (
            self.get_by_list_and_name_or_raise(lst, attribute_syn)
            if attribute_only_by_name
            else self.get_by_list_and_syn_or_raise(lst, attribute_syn)
        )

        return (community, member, lst, attr)
