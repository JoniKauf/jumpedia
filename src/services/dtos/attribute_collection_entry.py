from dataclasses import dataclass

from domain.entities.attribute_collection_entry import AttributeCollectionEntryEntity
from domain.value_objects.task_attribute_slot import TaskAttributeSlotStr


@dataclass(frozen=True, slots=True)
class CreateAttributeCollectionEntry:
    value: TaskAttributeSlotStr
    aliases: tuple[TaskAttributeSlotStr, ...]


@dataclass(frozen=True, slots=True)
class AttributeCollectionEntryEntityWithAliases:
    entry: AttributeCollectionEntryEntity
    aliases: tuple[TaskAttributeSlotStr, ...]
