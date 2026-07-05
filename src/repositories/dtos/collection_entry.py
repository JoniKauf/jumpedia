from dataclasses import dataclass

from domain.entities.collection_entry import CollectionEntryEntity
from domain.types.attribute import AttributeID
from domain.types.collection_entry import CollectionEntryID
from domain.value_objects.field_slot import FieldSlotStr
from domain.value_objects.index import Index


@dataclass(frozen=True, slots=True)
class CollectionEntryInsert:
    attribute_id: AttributeID
    index: Index
    value: FieldSlotStr


@dataclass(frozen=True, slots=True)
class CollectionEntryAliasInsert:
    collection_entry_id: CollectionEntryID
    index: Index
    attribute_id: AttributeID
    alias: FieldSlotStr


@dataclass(frozen=True, slots=True)
class CollectionEntryEntityWithAliases:
    entry: CollectionEntryEntity
    aliases: tuple[FieldSlotStr, ...]
