import typing as t
from dataclasses import dataclass

from domain import errors
from domain.entities.attribute import AttributeEntity
from domain.entities.attribute_collection_entry import AttributeCollectionEntryEntity
from domain.entities.community import CommunityEntity
from domain.entities.community_user import CommunityUserEntity
from domain.entities.list import ListEntity
from domain.enums.attribute import AttributeKind, AttributeType
from domain.enums.rank import CommunityRank
from domain.value_objects.attribute import AttributeSlot, AttributeSyn
from domain.value_objects.attribute_collection_entry import AttributeCollectionEntrySyn
from domain.value_objects.community import CommunityLimits, CommunityName
from domain.value_objects.list import ListName
from repositories.attribute import AttributeRepository
from repositories.attribute_collection_entry import AttributeCollectionEntryRepository
from repositories.dtos.attribute import AttributeAliasInsert, AttributeInsert
from repositories.dtos.attribute_collection_entry import (
    AttributeCollectionEntryAliasInsert,
    AttributeCollectionEntryInsert,
)
from services.community import CommunityAccessService
from services.community_user import CommunityUserAccessService
from services.contexts.interacting_user import InteractingUserContext
from services.dtos.attribute import AttributeInfo, AttributeSummary, DeletedAttribute
from services.dtos.attribute_collection_entry import CreateAttributeCollectionEntry
from services.list import ListAccessService
from services.permission import PermissionService


@dataclass(frozen=True, slots=True, eq=False)
class AttributeService:
    _attribute_repo: AttributeRepository
    _attribute_collection_entry_repo: AttributeCollectionEntryRepository
    _permission_service: PermissionService
    _list_access_service: ListAccessService
    _attribute_access_service: AttributeAccessService

    def create(
        self,
        name: AttributeSyn,
        type: t.Literal[AttributeType.TASK, AttributeType.USER],
        slot: AttributeSlot,
        aliases: tuple[AttributeSyn, ...],
        collection_entries: tuple[CreateAttributeCollectionEntry, ...],
        list_name: ListName | None,
    ) -> AttributeEntity:
        # --- Get Data ---
        community, community_user, lst = self._list_access_service.get_convenient(
            None, list_name
        )

        # --- Verify Rank ---
        self._permission_service.ensure_community_rank(
            community_user, CommunityRank.ADMINISTRATOR
        )

        # --- Verify Limit Of Count Not Exceeded ---
        # pos starts at 1 so max_pos == count
        attr_count = self._attribute_repo.count_by_list(lst.id)

        if attr_count >= community.limits.list_attribute_count_max:
            raise errors.CountLimitReached(
                community.limits.list_attribute_count_max, AttributeEntity
            )

        syns: tuple[AttributeSyn, ...] = (name, *aliases)

        if len(aliases) > community.limits.attribute_alias_count_max:
            raise errors.AliasCountLimitReached(
                community.limits.attribute_alias_count_max, name
            )

        # --- Verify Syn Uniquness Across Each Other And Across All Attributes ---
        AttributeSyn.raise_if_not_norm_unique(syns)

        existing_same_syn = self._attribute_repo.get_by_list_id_and_any_syn(
            lst.id, syns
        )

        if existing_same_syn is not None:
            raise errors.SynAlreadyTaken(existing_same_syn)

        # --- Validate Slot ---
        if slot.min_count != 0:
            raise errors.InitialSlotCountMustBeZero()

        # Check slot count max does not exceed community limit here, because in Slot itself we don't know the community's limit
        if slot.max_count > community.limits.attribute_task_value_slot_count_max:
            raise errors.SlotCountDefinitionLimitExceeded(
                slot.min_count,
                slot.max_count,
                CommunityLimits.ATTRIBUTE_TASK_VALUE_MIN_MIN_SLOT_COUNT,
                CommunityLimits.ATTRIBUTE_TASK_VALUE_MIN_MAX_SLOT_COUNT,
                community.limits.attribute_task_value_slot_count_max,
            )

        # --- Validate Collection ---
        if collection_entries:
            AttributeCollectionEntrySyn.raise_if_not_norm_unique(
                syn
                for entry in collection_entries
                for syn in (entry.value, *entry.aliases)
            )

            if (
                len(collection_entries)
                > community.limits.attribute_collection_entry_count_max
            ):
                raise errors.CountLimitReached(
                    community.limits.attribute_collection_entry_count_max,
                    AttributeCollectionEntryEntity,
                )

            for entry in collection_entries:
                if (
                    len(entry.aliases)
                    > community.limits.attribute_collection_entry_alias_count_max
                ):
                    raise errors.AliasCountLimitReached(
                        community.limits.attribute_collection_entry_alias_count_max,
                        entry.value,
                    )

            # Collection doesn't exist before so here we don't have to check for uniqueness across other db entries

        # --- Create Attribute ---
        attr_entity = self._attribute_repo.create(
            AttributeInsert(
                lst._id, name, type, AttributeKind.NONE, slot, attr_count + 1
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

    def delete(
        self, name: AttributeSyn, list_name: ListName | None
    ) -> DeletedAttribute:
        _, community_user, lst, attr = self._attribute_access_service.get_convenient(
            None, list_name, name
        )

        self._permission_service.ensure_community_rank(
            community_user, CommunityRank.ADMINISTRATOR
        )

        self._attribute_repo.delete(attr.id)
        self._attribute_repo.decrement_positions_after(lst.id, attr.position)

        return DeletedAttribute(
            attr.name, lst, attr.type, attr.kind, attr.slot, attr.position
        )


@dataclass(frozen=True, slots=True, eq=False)
class AttributeQueryService:
    _attribute_repo: AttributeRepository
    _community_access_service: CommunityAccessService
    _community_user_access_service: CommunityUserAccessService
    _list_access_service: ListAccessService
    _attribute_access_service: AttributeAccessService

    def info(self, name: AttributeSyn, list_name: ListName | None) -> AttributeInfo:
        _, _, lst = self._list_access_service.get_convenient(None, list_name)

        attr = self._attribute_access_service.get_by_list_and_name_or_raise(lst, name)

        return AttributeInfo(
            attr.name, lst, attr.type, attr.kind, attr.slot, attr.position
        )

    def summaries(
        self,
        list_name: ListName | None,
    ) -> tuple[AttributeSummary, ...]:
        _, _, lst = self._list_access_service.get_convenient(None, list_name)

        attrs = self._attribute_repo.get_all_by_list_id(
            lst.id,
        )

        return tuple(
            AttributeSummary(
                attr.name,
                lst,
                attr.type,
                attr.kind,
                attr.slot,
                attr.position,
            )
            for attr in attrs
        )


@dataclass(frozen=True, slots=True, eq=False)
class AttributeAccessService:
    _ctx: InteractingUserContext
    _repo: AttributeRepository
    _list_access_service: ListAccessService

    def get_by_list_and_name_or_raise(
        self, lst: ListEntity, name: AttributeSyn
    ) -> AttributeEntity:
        attr = self._repo.get_by_list_id_and_name(lst.id, name)

        if attr is None:
            raise errors.NotFoundByName(name, AttributeEntity)

        return attr

    def get_convenient(
        self,
        community_name: CommunityName | None,
        list_name: ListName | None,
        attribute_name: AttributeSyn,
    ) -> tuple[CommunityEntity, CommunityUserEntity, ListEntity, AttributeEntity]:
        community, community_user, lst = self._list_access_service.get_convenient(
            community_name, list_name
        )
        attr = self.get_by_list_and_name_or_raise(lst, attribute_name)

        return (community, community_user, lst, attr)
