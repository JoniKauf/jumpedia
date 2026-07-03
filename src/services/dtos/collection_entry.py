from dataclasses import dataclass

from domain.entities.collection_entry import CollectionEntryEntity
from domain.value_objects.field_slot import FieldSlotStr


@dataclass(frozen=True, slots=True)
class CreateCollectionEntry:
    value: FieldSlotStr
    aliases: tuple[FieldSlotStr, ...]


@dataclass(frozen=True, slots=True)
class CollectionEntryEntityWithAliases:
    entry: CollectionEntryEntity
    aliases: tuple[FieldSlotStr, ...]
