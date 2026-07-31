from dataclasses import dataclass

from jumpedia.domain.entities.attribute import AttributeEntity
from jumpedia.domain.entities.collection_entry import CollectionEntryEntity
from jumpedia.domain.entities.list import ListEntity
from jumpedia.domain.enums.attribute import AttributeKind, AttributeType
from jumpedia.domain.typing.attribute import AttributeID
from jumpedia.domain.typing.collection_entry import FrozenCollectionT
from jumpedia.domain.typing.list import ListID
from jumpedia.domain.value_objects.attribute import (
    AttributeFieldConfig,
    AttributeSynStr,
)
from jumpedia.domain.value_objects.position import Position


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
