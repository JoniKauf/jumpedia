from dataclasses import dataclass

from domain.entities.attribute import AttributeEntity
from domain.entities.list import ListEntity
from domain.enums.attribute import AttributeKind, AttributeType
from domain.types.list import ListID
from domain.value_objects.attribute import AttributeName, AttributeSlot


@dataclass(frozen=True, slots=True)
class AttributeInfoDTO:
    name: AttributeName
    list: ListEntity
    type: AttributeType
    kind: AttributeKind
    slot: AttributeSlot
    position: int


@dataclass(frozen=True, slots=True)
class AttributeSummaryDTO:
    name: AttributeName
    list: ListEntity
    type: AttributeType
    kind: AttributeKind
    slot: AttributeSlot
    position: int

@dataclass(frozen=True, slots=True)
class DeletedAttributeDTO:
    name: AttributeName
    list: ListEntity
    type: AttributeType
    kind: AttributeKind
    slot: AttributeSlot
    position: int