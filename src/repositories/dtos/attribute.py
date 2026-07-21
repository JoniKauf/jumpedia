from dataclasses import dataclass

from domain.enums.attribute import AttributeKind, AttributeType
from domain.typing.attribute import AttributeID
from domain.typing.list import ListID
from domain.value_objects.attribute import AttributeFieldConfig, AttributeSynStr
from domain.value_objects.index import Index
from domain.value_objects.position import Position


@dataclass(frozen=True, slots=True)
class AttributeInsert[T: AttributeType]:
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
