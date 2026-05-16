
from dataclasses import dataclass

from domain import errors
from domain.entities.base import BaseEntity
from domain.value_objects.limits import Limits
from domain.value_objects.strings import StrStore

@dataclass(slots=True)
class CommunityEntity(BaseEntity):
    _name: StrStore
    _limits: Limits

    def __post_init__(self) -> None:
        super().__post_init__()

        if len(self._name.real) > Limits.COMMUNITY_NAME_LENGTH_MAX:
            raise errors

    @property
    def name(self) -> StrStore:
        return self._name

    @property
    def limits(self) -> Limits:
        return self._limits
