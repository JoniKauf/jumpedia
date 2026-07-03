import typing as t
from dataclasses import dataclass

from domain import errors
from domain.entities.attribute import AttributeEntity
from domain.entities.collection_entry import CollectionEntryEntity
from domain.entities.community import CommunityEntity
from domain.entities.community_user import CommunityUserEntity
from domain.entities.list import ListEntity
from domain.enums.attribute import AttributeKind, AttributeType
from domain.enums.rank import CommunityRank
from domain.value_objects.attribute import AttributeSlot, AttributeSynStr
from domain.value_objects.community import CommunityLimits, CommunityNameStr
from domain.value_objects.index import Index
from domain.value_objects.list import ListNameStr
from domain.value_objects.position import Position
from domain.value_objects.field_slot import FieldSlotStr
from repositories.attribute import AttributeRepository
from repositories.collection_entry import CollectionEntryRepository
from repositories.dtos.attribute import AttributeAliasInsert, AttributeInsert
from repositories.dtos.collection_entry import (
    CollectionEntryAliasInsert,
    CollectionEntryInsert,
)
from services.community import CommunityAccessService
from services.community_user import CommunityUserAccessService
from services.contexts.interacting_user import InteractingUserContext
from services.dtos.attribute import AttributeInfo, AttributeSummary, DeletedAttribute
from services.dtos.collection_entry import (
    CollectionEntryEntityWithAliases,
    CreateCollectionEntry,
)
from services.list import ListAccessService
from services.permission import PermissionService


@dataclass(frozen=True, slots=True, eq=False)
class AttributeService:
    _attribute_repo: AttributeRepository
    _collection_entry_repo: CollectionEntryRepository
    _permission_service: PermissionService
    _list_access_service: ListAccessService
    _attribute_access_service: AttributeAccessService

    def create[T: AttributeType.TaskT | AttributeType.UserT](
        self,
        name: AttributeSynStr,
        list_name: ListNameStr,
        type: T,
        slot: AttributeSlot,
        aliases: tuple[AttributeSynStr, ...],
        collection_entries: tuple[CreateCollectionEntry, ...],
    ) -> AttributeEntity[T]:
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
        attr_count = self._attribute_repo.count_by_list(lst.list_id)

        if attr_count >= community.limits.list_attribute_count_max:
            raise errors.CountLimitReached(
                community.limits.list_attribute_count_max, AttributeEntity
            )

        syns: tuple[AttributeSynStr, ...] = (name, *aliases)

        if len(aliases) > community.limits.attribute_alias_count_max:
            raise errors.AliasCountLimitReached(
                community.limits.attribute_alias_count_max, name
            )

        # --- Verify Syn Uniquness Across Each Other And Across All Attributes ---
        AttributeSynStr.raise_if_not_norm_unique(syns)

        existing_same_syn = self._attribute_repo.get_by_list_id_and_any_syn(
            lst.list_id, syns
        )

        if existing_same_syn is not None:
            raise errors.SynAlreadyTaken(*existing_same_syn)

        # --- Validate Slot ---
        if slot.min_count != 0:
            raise errors.InitialSlotCountMustBeZero()

        # Check slot count max does not exceed community limit here, because in Slot itself we don't know the community's limit
        if slot.max_count > community.limits.field_slot_count_max:
            raise errors.SlotCountDefinitionLimitExceeded(
                slot.min_count,
                slot.max_count,
                CommunityLimits.FIELD_MIN_MIN_SLOT_COUNT,
                CommunityLimits.FIELD_MIN_MAX_SLOT_COUNT,
                community.limits.field_slot_count_max,
            )

        # --- Validate Collection ---
        if collection_entries:
            FieldSlotStr.raise_if_not_norm_unique(
                syn
                for entry in collection_entries
                for syn in (entry.value, *entry.aliases)
            )

            if (
                len(collection_entries)
                > community.limits.collection_entry_count_max
            ):
                raise errors.CountLimitReached(
                    community.limits.collection_entry_count_max,
                    CollectionEntryEntity,
                )

            for entry in collection_entries:
                if (
                    len(entry.aliases)
                    > community.limits.collection_entry_alias_count_max
                ):
                    raise errors.AliasCountLimitReached(
                        community.limits.collection_entry_alias_count_max,
                        entry.value,
                    )

            # Collection doesn't exist before so here we don't have to check for uniqueness across other db entries

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
        if collection_entries:
            created_entries: tuple[CollectionEntryEntity, ...] = (
                self._collection_entry_repo.create_many(
                    CollectionEntryInsert(
                        attr_entity.attribute_id, Index(i), entry.value
                    )
                    for i, entry in enumerate(collection_entries)
                )
            )

            all_aliases: list[CollectionEntryAliasInsert] = []

            for i, created_entry in enumerate(created_entries):
                for i, alias in enumerate(collection_entries[i].aliases):
                    alias_insert = CollectionEntryAliasInsert(
                        created_entry.collection_entry_id,
                        Index(i),
                        created_entry.attribute_id,
                        alias,
                    )

                    all_aliases.append(alias_insert)

            self._collection_entry_repo.create_many_aliases(all_aliases)

        return attr_entity

    def delete(self, name: AttributeSynStr, list_name: ListNameStr) -> DeletedAttribute:
        _, community_user, lst, attr = self._attribute_access_service.get_convenient(
            None, list_name, name, True
        )

        self._permission_service.ensure_community_rank(
            community_user, CommunityRank.ADMINISTRATOR
        )

        self._attribute_repo.delete(attr.attribute_id)
        self._attribute_repo.decrement_positions_after(lst.list_id, attr.position)

        return DeletedAttribute(
            attr.name, lst, attr.type, attr.kind, attr.slot, attr.position
        )


@dataclass(frozen=True, slots=True, eq=False)
class AttributeQueryService:
    _attribute_repo: AttributeRepository
    _collection_entry_repo: CollectionEntryRepository
    _community_access_service: CommunityAccessService
    _community_user_access_service: CommunityUserAccessService
    _list_access_service: ListAccessService
    _attribute_access_service: AttributeAccessService

    def info(
        self, syn: AttributeSynStr, list_name: ListNameStr | None
    ) -> AttributeInfo:
        _, _, lst, attr = self._attribute_access_service.get_convenient(
            None, list_name, syn, False
        )

        aliases = self._attribute_repo.get_aliases_by_attribute_id(attr.attribute_id)
        collection = (
            self._collection_entry_repo.get_collection_by_attribute_id(
                attr.attribute_id
            )
        )

        return AttributeInfo(
            attr.name,
            aliases,
            lst,
            attr.type,
            attr.kind,
            attr.slot,
            attr.position,
            tuple(
                CollectionEntryEntityWithAliases(entry.entry, entry.aliases)
                for entry in collection
            ),
        )

    def summaries(
        self,
        list_name: ListNameStr | None,
    ) -> tuple[AttributeSummary, ...]:
        _, _, lst = self._list_access_service.get_convenient(None, list_name)

        ATTRIBUTE_TYPES: t.Final = AttributeType.ALL()

        attrs = self._attribute_repo.get_all_by_list_id(lst.list_id, ATTRIBUTE_TYPES)

        attr_id_to_aliases = self._attribute_repo.get_grouped_aliases_by_list_id(
            lst.list_id, ATTRIBUTE_TYPES
        )
        attr_id_to_collection = (
            self._collection_entry_repo.get_grouped_collections_by_list_id(
                lst.list_id, ATTRIBUTE_TYPES
            )
        )

        return tuple(
            AttributeSummary(
                attr.name,
                attr_id_to_aliases[attr.attribute_id],
                lst,
                attr.type,
                attr.kind,
                attr.slot,
                attr.position,
                tuple(
                    CollectionEntryEntityWithAliases(
                        entry.entry, entry.aliases
                    )
                    for entry in attr_id_to_collection[attr.attribute_id]
                ),
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
            raise errors.NotFoundByName(name, AttributeEntity)

        return attr

    def get_by_list_and_syn_or_raise(
        self, lst: ListEntity, syn: AttributeSynStr
    ) -> AttributeEntity:
        attr = self._repo.get_by_list_id_and_syn(lst.list_id, syn)

        if attr is None:
            raise errors.NotFoundBySyn(syn, AttributeEntity)

        return attr

    def get_convenient(
        self,
        community_name: CommunityNameStr | None,
        list_name: ListNameStr | None,
        attribute_syn: AttributeSynStr,
        attribute_only_by_name: bool,
    ) -> tuple[CommunityEntity, CommunityUserEntity, ListEntity, AttributeEntity]:
        community, community_user, lst = self._list_access_service.get_convenient(
            community_name, list_name
        )
        attr = (
            self.get_by_list_and_name_or_raise(lst, attribute_syn)
            if attribute_only_by_name
            else self.get_by_list_and_syn_or_raise(lst, attribute_syn)
        )

        return (community, community_user, lst, attr)
