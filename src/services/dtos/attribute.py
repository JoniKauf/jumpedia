from dataclasses import dataclass

from domain.entities.attribute import AttributeEntity
from domain.entities.attribute_collection_entry import AttributeCollectionEntryEntity
from domain.entities.list import ListEntity
from domain.enums.attribute import AttributeKind, AttributeType
from domain.types.list import ListID
from domain.value_objects.attribute import AttributeSlot, AttributeSynStr
from domain.value_objects.position import Position
from services.dtos.attribute_collection_entry import (
    AttributeCollectionEntryEntityWithAliases,
)


@dataclass(frozen=True, slots=True)
class AttributeInfo:
    name: AttributeSynStr
    aliases: tuple[AttributeSynStr, ...]
    list: ListEntity
    type: AttributeType
    kind: AttributeKind
    slot: AttributeSlot
    position: Position
    collection: tuple[AttributeCollectionEntryEntityWithAliases, ...]


@dataclass(frozen=True, slots=True)
class AttributeSummary:
    name: AttributeSynStr
    aliases: tuple[AttributeSynStr, ...]
    list: ListEntity
    type: AttributeType
    kind: AttributeKind
    slot: AttributeSlot
    position: Position
    collection: tuple[AttributeCollectionEntryEntityWithAliases, ...]


@dataclass(frozen=True, slots=True)
class DeletedAttribute:
    name: AttributeSynStr
    list: ListEntity
    type: AttributeType
    kind: AttributeKind
    slot: AttributeSlot
    position: Position
