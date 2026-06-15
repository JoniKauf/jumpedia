from dataclasses import dataclass

from domain.enums.attribute import AttributeKind, AttributeType
from domain.types.list import ListID
from domain.value_objects.attribute import AttributeSyn, AttributeSlot


@dataclass(frozen=True, slots=True)
class CreateAttributeDTO:
    list_id: ListID
    name: AttributeSyn
    type: AttributeType
    kind: AttributeKind
    slot: AttributeSlot
    position: int
