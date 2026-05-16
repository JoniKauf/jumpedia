
from dataclasses import dataclass

from domain.entities.base import BaseEntity
from domain.value_objects.limits import Limits
from domain.value_objects.strings import StrStore

@dataclass(kw_only=True, slots=True)
class CommunityEntity(BaseEntity):
    _name: StrStore
    _limits: Limits

    @property
    def name(self) -> StrStore:
        return self._name

    @property
    def limits(self) -> Limits:
        return self._limits
