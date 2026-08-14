from dataclasses import dataclass

from jumpedia.domain.enums.attribute import AttributeKind, AttributeType
from jumpedia.domain.typing.attribute import AnyAttributeTypeT, AttributeID
from jumpedia.domain.typing.list import ListID
from jumpedia.domain.value_objects.attribute import (
    AttributeFieldConfig,
    AttributeSynStr,
)
from jumpedia.domain.value_objects.index import Index
from jumpedia.domain.value_objects.position import Position


@dataclass(frozen=True, slots=True)
class AttributeInsert[T: AnyAttributeTypeT]:
    list_id: ListID
    name: AttributeSynStr
    type: T
    kind: AttributeKind
    field_config: AttributeFieldConfig
    position: Position


@dataclass(frozen=True, slots=True)
class AttributeAliasInsert:
    attribute_id: AttributeID
    index: Index
    list_id: ListID
    alias: AttributeSynStr
