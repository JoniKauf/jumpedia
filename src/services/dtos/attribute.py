from dataclasses import dataclass

from domain.entities.attribute import AttributeEntity
from domain.entities.list import ListEntity
from domain.enums.attribute import AttributeKind, AttributeType
from domain.types.list import ListID
from domain.value_objects.attribute import AttributeSyn, AttributeSlot


@dataclass(frozen=True, slots=True)
class AttributeInfoDTO:
    name: AttributeSyn
    list: ListEntity
    type: AttributeType
    kind: AttributeKind
    slot: AttributeSlot
    position: int


@dataclass(frozen=True, slots=True)
class AttributeSummaryDTO:
    name: AttributeSyn
    list: ListEntity
    type: AttributeType
    kind: AttributeKind
    slot: AttributeSlot
    position: int


@dataclass(frozen=True, slots=True)
class DeletedAttributeDTO:
    name: AttributeSyn
    list: ListEntity
    type: AttributeType
    kind: AttributeKind
    slot: AttributeSlot
    position: int
