from dataclasses import dataclass
from domain.entities.base import BaseEntity
from domain.value_objects.slot import Slot
from domain.value_objects.strings import StrStore

from domain.enums.attribute import Kind, Type

@dataclass(kw_only=True, slots=True)
class AttributeEntity(BaseEntity):
    _list_id: int
    _type: Type
    _kind: Kind
    _name: StrStore
    _slot: Slot
    _position: int

    def __post_init__(self) -> None:
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

    @property
    def slot(self) -> Slot:
        return self._slot

    @property
    def position(self) -> int:
        return self._position