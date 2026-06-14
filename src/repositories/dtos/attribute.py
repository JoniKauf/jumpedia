


from dataclasses import dataclass

from domain.enums.attribute import AttributeKind, AttributeType
from domain.types.id import ID
from domain.value_objects.attribute import AttributeName, AttributeSlot


@dataclass(frozen=True, slots=True)
class CreateAttributeDTO:
    list_id: ID
    name: AttributeName
    type: AttributeType
    kind: AttributeKind
    slot: AttributeSlot
    position: int