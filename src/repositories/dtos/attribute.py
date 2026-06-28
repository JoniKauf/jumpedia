from dataclasses import dataclass

from domain.enums.attribute import AttributeKind, AttributeType
from domain.types.attribute import AttributeID
from domain.types.list import ListID
from domain.value_objects.attribute import AttributeSlot, AttributeSynStr
from domain.value_objects.index import Index
from domain.value_objects.position import Position


@dataclass(frozen=True, slots=True)
class AttributeInsert:
    list_id: ListID
    name: AttributeSynStr
    type: AttributeType
    kind: AttributeKind
    slot: AttributeSlot
    position: Position


@dataclass(frozen=True, slots=True)
class AttributeAliasInsert:
    attribute_id: AttributeID
    index: Index
    list_id: ListID
    alias: AttributeSynStr
