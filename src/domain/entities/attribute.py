from domain import errors
from domain.entities.base import BaseEntity
from domain.enums.attribute import AttributeType, AttributeKind
from domain.types.id import ID
from domain.value_objects.limits import Limits
from domain.value_objects.slot import AttributeSlot
from domain.value_objects.string import StrStore


class AttributeEntity(BaseEntity):
    def __init__(
        self,
        id: ID,
        list_id: ID,
        type: AttributeType,
        kind: AttributeKind,
        name: StrStore,
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
    def list_id(self) -> ID:
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
    def name(self) -> StrStore:
        return self._name

    @name.setter
    def name(self, value: StrStore) -> None:
        if len(value) > Limits.ATTRIBUTE_SYN_LENGTH_MAX:
            raise errors.NameTooLong(
                value,
                Limits.ATTRIBUTE_SYN_LENGTH_MAX,
                AttributeEntity,
            )

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
