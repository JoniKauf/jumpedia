from dataclasses import dataclass

from jumpedia.domain.entities.collection_entry import CollectionEntryEntity
from jumpedia.domain.entities.community import CommunityEntity
from jumpedia.domain.enums.attribute import AttributeSlotType
from jumpedia.domain.enums.concept import Concept
from jumpedia.domain.errors.business import AliasCountLimitSurpassed, CountLimitReached
from jumpedia.domain.typing.collection_entry import (
    AbstractCollectionT,
    FrozenCollectionT,
)
from jumpedia.domain.value_objects.field_slot import FieldSlotStr
from jumpedia.services.internal.slot_type import SlotTypeService
from jumpedia.services.internal.strs import StrsService


@dataclass(frozen=True, slots=True, eq=False)
class CollectionBuildService:
    _slot_type_service: SlotTypeService
    _strs_service: StrsService

    def build(
        self,
        collection: AbstractCollectionT,
        community: CommunityEntity,
        slot_type: AttributeSlotType,
    ) -> FrozenCollectionT:
        if len(collection) > community.limits.collection_entry_count_max:
            raise CountLimitReached(
                Concept.COLLECTION,
                community.limits.collection_entry_count_max,
            )

        for entry in collection:
            if len(entry[1]) > community.limits.collection_entry_alias_count_max:
                raise AliasCountLimitSurpassed(
                    community.limits.collection_entry_alias_count_max,
                    entry[0],
                    entry[1],
                )

        self._strs_service.validate_unique_collection_syns(collection)

        entries: list[tuple[FieldSlotStr, tuple[FieldSlotStr, ...]]] = []

        for value, aliases in collection:
            value = self._slot_type_service.single_to_slot_typed_str(value, slot_type)

            # Aliases do not need to be type checked
            entries.append((value, tuple(aliases)))

        return tuple(entries)
