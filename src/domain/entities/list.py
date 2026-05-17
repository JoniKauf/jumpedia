from domain import errors
from domain.entities.base import BaseEntity
from domain.value_objects.limits import Limits
from domain.value_objects.string import StrStore


class ListEntity(BaseEntity):
    def __init__(self, id: int, community_id: int, name: StrStore) -> None:
        super().__init__(id)
        self._community_id = community_id
        self._name = name

    @property
    def community_id(self) -> int:
        return self._community_id

    @property
    def name(self) -> StrStore:
        return self._name

    @name.setter
    def name(self, value: StrStore) -> None:
        if len(value) > Limits.LIST_NAME_LENGTH_MAX:
            raise errors.NameTooLong(value, ListEntity)

        self._name = value
