from dataclasses import dataclass

from domain.entities.attribute import AttributeEntity
from domain.entities.collection_entry import CollectionEntryEntity
from domain.entities.list import ListEntity
from domain.enums.attribute import AttributeKind, AttributeType
from domain.typing.attribute import AttributeID
from domain.typing.collection_entry import FrozenCollectionT
from domain.typing.list import ListID
from domain.value_objects.attribute import AttributeFieldConfig, AttributeSynStr
from domain.value_objects.position import Position


@dataclass(frozen=True, slots=True)
class AttributeInfo:
    attribute: AttributeEntity
    aliases: tuple[AttributeSynStr, ...]
    collection: FrozenCollectionT
    list: ListEntity


@dataclass(frozen=True, slots=True)
class AttributeSummary:
    name: AttributeSynStr
    aliases: tuple[AttributeSynStr, ...]
    list: ListEntity
    type: AttributeType
    kind: AttributeKind
    field_config: AttributeFieldConfig
    position: Position
    collection: FrozenCollectionT


@dataclass(frozen=True, slots=True)
class PreparedDeleteAttribute:
    list_id: ListID
    attribute_id: AttributeID
    attribute_position: Position
