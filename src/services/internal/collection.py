from dataclasses import dataclass

from domain.entities.collection_entry import CollectionEntryEntity
from domain.entities.community import CommunityEntity
from domain.enums.attribute import AttributeSlotType
from domain.errors.business import AliasCountLimitSurpassed, CountLimitReached, SynsNotUnique, NotUniqueSynsAcrossNamesAndAliases
from domain.typing.collection_entry import AbstractCollectionT, FrozenCollectionT
from domain.value_objects.field_slot import FieldSlotStr
from services.internal.slot_type import SlotTypeService
from services.internal.strs import StrsService


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
                community.limits.collection_entry_count_max,
                CollectionEntryEntity,
            )

        for entry in collection:
            if len(entry[1]) > community.limits.collection_entry_alias_count_max:
                raise AliasCountLimitSurpassed(
                    community.limits.collection_entry_alias_count_max,
                    entry[0],
                    entry[1],
                )

        syn_to_name_and_alias: dict[FieldSlotStr, tuple[FieldSlotStr, FieldSlotStr | None]] = {}

        for name, aliases in collection:
            syn_is_name: bool = True

            for syn in (name, *aliases):
                seen = syn_to_name_and_alias.get(syn)

                if seen is not None:
                    seen_name, seen_alias = seen

                    raise NotUniqueSynsAcrossNamesAndAliases(
                        seen_name,
                        name,
                        seen_alias,
                        None if syn_is_name else syn
                    )

                syn_to_name_and_alias[syn] = (name, None if syn_is_name else syn)

                syn_is_name = False
                
        entries: list[tuple[FieldSlotStr, tuple[FieldSlotStr, ...]]] = []

        for value, aliases in collection:
            value = self._slot_type_service.single_to_slot_typed_str(value, slot_type)

            # Aliases do not need to be type checked
            entries.append((value, tuple(aliases)))

        return tuple(entries)
