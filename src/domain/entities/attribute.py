from domain.entities.base import BaseEntity
from domain.enums.attribute import AttributeKind, AttributeType
from domain.types.attribute import AttributeID
from domain.types.list import ListID
from domain.value_objects.attribute import AttributeSlot, AttributeSynStr
from domain.value_objects.position import Position
import typing as t


class AttributeEntity[T: AttributeType = AttributeType](BaseEntity[AttributeID]):
    def __init__(
        self,
        attribute_id: AttributeID,
        list_id: ListID,
        name: AttributeSynStr,
        type: T,
        kind: AttributeKind,
        slot: AttributeSlot,
        position: Position,
    ) -> None:
        super().__init__(attribute_id)

        self._list_id = list_id
        self._type = type
        self._kind = kind
        self.name = name
        self.slot = slot
        self.position = position

    @property
    def attribute_id(self) -> AttributeID:
        return self._composite_key[0]

    @property
    def list_id(self) -> ListID:
        return self._list_id

    @property
    def type(self) -> T:
        return self._type

    @property
    def kind(self) -> AttributeKind:
        return self._kind

    @property
    def name(self) -> AttributeSynStr:
        return self._name

    @name.setter
    def name(self, value: AttributeSynStr) -> None:
        self._name = value

    @property
    def slot(self) -> AttributeSlot:
        return self._slot

    @slot.setter
    def slot(self, value: AttributeSlot) -> None:
        self._slot = value

    @property
    def position(self) -> Position:
        return self._position

    @position.setter
    def position(self, value: Position) -> None:
        self._position = value

    @property
    def slot_unique_across_list(self) -> bool:
        return self.type is AttributeType.STATIC

    type OfTypeStaticT = AttributeEntity[AttributeType.StaticT]
    type OfTypeTaskT = AttributeEntity[AttributeType.TaskT]
    type OfTypeUserT = AttributeEntity[AttributeType.UserT]

    type OfTypeNotUserT = AttributeEntity[AttributeType.StaticT | AttributeType.TaskT]
    type OfTypeNotStaticT = AttributeEntity[AttributeType.TaskT | AttributeType.UserT]

    type OfAnyTypeT = AttributeEntity[AttributeType.AllT]

    type AllStaticT = tuple[OfTypeStaticT, OfTypeStaticT, OfTypeStaticT]
