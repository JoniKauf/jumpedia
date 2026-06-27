from dataclasses import dataclass

from domain.entities.attribute_collection_entry import AttributeCollectionEntryEntity
from domain.types.attribute import AttributeID
from domain.types.attribute_collection_entry import AttributeCollectionEntryID
from domain.value_objects.index import Index
from domain.value_objects.task_attribute_slot import TaskAttributeSlot


@dataclass(frozen=True, slots=True)
class AttributeCollectionEntryInsert:
    attribute_id: AttributeID
    index: Index
    value: TaskAttributeSlot


@dataclass(frozen=True, slots=True)
class AttributeCollectionEntryAliasInsert:
    attribute_collection_entry_id: AttributeCollectionEntryID
    attribute_id: AttributeID
    alias: TaskAttributeSlot


@dataclass(frozen=True, slots=True)
class AttributeCollectionEntryWithAliases:
    entry: AttributeCollectionEntryEntity
    aliases: tuple[TaskAttributeSlot, ...]