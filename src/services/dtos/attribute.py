from dataclasses import dataclass

from domain.entities.attribute import AttributeEntity
from domain.entities.list import ListEntity
from domain.enums.attribute import AttributeKind, AttributeType
from domain.types.list import ListID
from domain.value_objects.attribute import AttributeSlot, AttributeSyn


@dataclass(frozen=True, slots=True)
class AttributeInfo:
    name: AttributeSyn
    list: ListEntity
    type: AttributeType
    kind: AttributeKind
    slot: AttributeSlot
    position: int


@dataclass(frozen=True, slots=True)
class AttributeSummary:
    name: AttributeSyn
    list: ListEntity
    type: AttributeType
    kind: AttributeKind
    slot: AttributeSlot
    position: int


@dataclass(frozen=True, slots=True)
class DeletedAttribute:
    name: AttributeSyn
    list: ListEntity
    type: AttributeType
    kind: AttributeKind
    slot: AttributeSlot
    position: int
