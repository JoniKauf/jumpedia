from dataclasses import dataclass

from domain.entities.attribute_collection_entry import AttributeCollectionEntryEntity
from domain.types.attribute import AttributeID
from domain.types.attribute_collection_entry import AttributeCollectionEntryID
from domain.value_objects.index import Index
from domain.value_objects.task_attribute_slot import TaskAttributeSlotStr


@dataclass(frozen=True, slots=True)
class AttributeCollectionEntryInsert:
    attribute_id: AttributeID
    index: Index
    value: TaskAttributeSlotStr


@dataclass(frozen=True, slots=True)
class AttributeCollectionEntryAliasInsert:
    attribute_collection_entry_id: AttributeCollectionEntryID
    index: Index
    attribute_id: AttributeID
    alias: TaskAttributeSlotStr


@dataclass(frozen=True, slots=True)
class AttributeCollectionEntryEntityWithAliases:
    entry: AttributeCollectionEntryEntity
    aliases: tuple[TaskAttributeSlotStr, ...]
