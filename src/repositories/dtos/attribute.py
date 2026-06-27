from dataclasses import dataclass

from domain.enums.attribute import AttributeKind, AttributeType
from domain.types.attribute import AttributeID
from domain.types.list import ListID
from domain.value_objects.attribute import AttributeSlot, AttributeSyn
from domain.value_objects.position import Position


@dataclass(frozen=True, slots=True)
class AttributeInsert:
    list_id: ListID
    name: AttributeSyn
    type: AttributeType
    kind: AttributeKind
    slot: AttributeSlot
    position: Position


@dataclass(frozen=True, slots=True)
class AttributeAliasInsert:
    attribute_id: AttributeID
    list_id: ListID
    alias: AttributeSyn
