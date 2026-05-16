
from dataclasses import dataclass

from domain.entities.base import BaseEntity
from domain.value_objects.strings import StrStore

@dataclass(slots=True)
class ListEntity(BaseEntity):
    _community_id: int
    _name: StrStore

    @property
    def community_id(self) -> int:
        return self._community_id

    @property
    def name(self) -> StrStore:
        return self._name
    
    @name.setter
    def name(self, name: StrStore) -> None:
        self._name = name