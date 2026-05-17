from domain import errors
from domain.entities.base import BaseEntity
from domain.value_objects.limits import Limits
from domain.value_objects.string import StrStore


class CommunityEntity(BaseEntity):
    _name: StrStore
    _limits: Limits

    def __init__(self, id: int, name: StrStore, limits: Limits) -> None:
        super().__init__(id)
        self.name = name
        self.limits = limits

    @property
    def name(self) -> StrStore:
        return self._name

    @name.setter
    def name(self, value: StrStore) -> None:
        if len(self._name.real) > Limits.COMMUNITY_NAME_LENGTH_MAX:
            raise errors.NameTooLong(value, Limits.COMMUNITY_NAME_LENGTH_MAX, type(self))

        self._name = value

    @property
    def limits(self) -> Limits:
        return self._limits
    
    @limits.setter
    def limits(self, value: Limits) -> None:
        self._limits = value
