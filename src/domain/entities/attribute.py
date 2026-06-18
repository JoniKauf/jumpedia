from domain.entities.base import BaseEntity
from domain.enums.attribute import AttributeKind, AttributeType
from domain.types.attribute import AttributeID
from domain.types.list import ListID
from domain.value_objects.attribute import AttributeSlot, AttributeSyn


class AttributeEntity(BaseEntity[AttributeID]):
    def __init__(
        self,
        id: AttributeID,
        list_id: ListID,
        name: AttributeSyn,
        type: AttributeType,
        kind: AttributeKind,
        slot: AttributeSlot,
        position: int,
    ) -> None:
        super().__init__(id)

        self._list_id = list_id
        self._type = type
        self._kind = kind
        self.name = name
        self.slot = slot
        self.position = position

    @property
    def list_id(self) -> ListID:
        return self._list_id

    @property
    def type(self) -> AttributeType:
        return self._type

    @property
    def kind(self) -> AttributeKind:
        return self._kind

    @property
    def name(self) -> AttributeSyn:
        return self._name

    @name.setter
    def name(self, value: AttributeSyn) -> None:
        self._name = value

    @property
    def slot(self) -> AttributeSlot:
        return self._slot

    @slot.setter
    def slot(self, value: AttributeSlot) -> None:
        self._slot = value

    @property
    def position(self) -> int:
        return self._position

    @position.setter
    def position(self, value: int) -> None:
        if value < 1:
            raise ValueError("position < 1")

        self._position = value
