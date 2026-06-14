from domain.entities.base import BaseEntity
from domain.enums.attribute import AttributeType, AttributeKind
from domain.types.attribute import AttributeID
from domain.types.list import ListID
from domain.value_objects.attribute import AttributeName, AttributeSlot


class AttributeEntity(BaseEntity[AttributeID]):
    def __init__(
        self,
        id: AttributeID,
        list_id: ListID,
        name: AttributeName,
        type: AttributeType,
        kind: AttributeKind,
        slot: AttributeSlot,
        position: int,
    ) -> None:
        super().__init__(id)

        self._list_id = list_id
        self.type = type
        self.kind = kind
        self.name = name
        self.slot = slot
        self.position = position

    @property
    def list_id(self) -> ListID:
        return self._list_id

    @property
    def type(self) -> AttributeType:
        return self._type

    @type.setter
    def type(self, value: AttributeType) -> None:
        self._type = value

    @property
    def kind(self) -> AttributeKind:
        return self._kind

    @kind.setter
    def kind(self, value: AttributeKind) -> None:
        self._kind = value

    @property
    def name(self) -> AttributeName:
        return self._name

    @name.setter
    def name(self, value: AttributeName) -> None:
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
