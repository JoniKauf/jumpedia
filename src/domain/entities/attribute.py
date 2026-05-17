from domain import errors
from domain.entities.base import BaseEntity
from domain.enums.attribute import Type, Kind
from domain.value_objects.limits import Limits
from domain.value_objects.slot import Slot
from domain.value_objects.string import StrStore


class AttributeEntity(BaseEntity):
    def __init__(
        self,
        id: int,
        list_id: int,
        type: Type,
        kind: Kind,
        name: StrStore,
        slot: Slot,
        position: int,
    ) -> None:
        super().__init__(id)
        self._list_id = list_id
        self._type = type
        self._kind = kind
        self.name = name
        self._slot = slot
        self._position = position

        if self._position < 1:
            raise ValueError("position < 1")

    @property
    def list_id(self) -> int:
        return self._list_id

    @property
    def type(self) -> Type:
        return self._type

    @property
    def kind(self) -> Kind:
        return self._kind

    @property
    def name(self) -> StrStore:
        return self._name

    @name.setter
    def name(self, value: StrStore) -> None:
        if len(value) > Limits.ATTRIBUTE_SYN_LENGTH_MAX:
            raise errors.NameTooLong(value, Limits.ATTRIBUTE_SYN_LENGTH_MAX, AttributeEntity)
        self._name = value

    @property
    def slot(self) -> Slot:
        return self._slot

    @property
    def position(self) -> int:
        return self._position
