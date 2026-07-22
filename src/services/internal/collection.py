from dataclasses import dataclass

from domain.entities.collection_entry import CollectionEntryEntity
from domain.entities.community import CommunityEntity
from domain.enums.attribute import AttributeSlotType
from domain.errors import business
from domain.typing.collection_entry import AbstractCollectionT, FrozenCollectionT
from domain.value_objects.field_slot import FieldSlotStr
from services.internal.slot_type import SlotTypeService



@dataclass(frozen=True, slots=True, eq=False)
class CollectionBuildService:
    _slot_type_service: SlotTypeService

    def build(self, collection: AbstractCollectionT, community: CommunityEntity, slot_type: AttributeSlotType) -> FrozenCollectionT:
        if len(collection) > community.limits.collection_entry_count_max:
            raise business.CountLimitReached(
                community.limits.collection_entry_count_max,
                CollectionEntryEntity,
            )

        for entry in collection:
            if len(entry[1]) > community.limits.collection_entry_alias_count_max:
                raise business.AliasCountLimitReached(
                    community.limits.collection_entry_alias_count_max,
                    entry[0],
                    entry[1],
                )

        FieldSlotStr.raise_if_not_unique(
            syn for entry in collection for syn in (entry[0], *entry[1])
        )

        entries: list[tuple[FieldSlotStr, tuple[FieldSlotStr, ...]]] = []

        for value, aliases in collection:
            value = self._slot_type_service.single_to_slot_typed_str(value, slot_type)

            # Aliases do not need to be type checked
            entries.append((value, tuple(aliases)))

        return tuple(entries)