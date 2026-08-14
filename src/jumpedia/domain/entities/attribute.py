from jumpedia.domain.entities.base import BaseEntity

lazy from jumpedia.domain.enums.attribute import AttributeKind, AttributeType
from jumpedia.domain.errors.internal import AttributeTypeKindMismatch
from jumpedia.domain.typing.attribute import AnyAttributeTypeT, AttributeID

lazy from jumpedia.domain.typing.list import ListID
lazy from jumpedia.domain.value_objects.attribute import (
    AttributeFieldConfig,
    AttributeSynStr,
)
lazy from jumpedia.domain.value_objects.position import Position
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AttributeEntity[T: AnyAttributeTypeT = AnyAttributeTypeT](
    BaseEntity[AttributeID]
):
    list_id: ListID
    type: T
    kind: AttributeKind
    name: AttributeSynStr
    field_config: AttributeFieldConfig
    position: Position

    def __post_init__(self) -> None:
        if self.kind is not AttributeKind.NONE and self.kind.type is not self.type:
            raise AttributeTypeKindMismatch(self.attribute_id, self.type, self.kind)

    @property
    def attribute_id(self) -> AttributeID:
        return self.key[0]

    @property
    def slot_unique_across_list(self) -> bool:
        return self.kind in (AttributeKind.ID, AttributeKind.NAME, AttributeKind.ALIAS)
