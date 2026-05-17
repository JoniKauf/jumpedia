import typing as t

from domain.entities.base import BaseEntity
from domain.value_objects.string import StrStore

class MentionableEntity(t.Protocol):
    @property
    def __class__(self) -> type[BaseEntity]:
        ...

    @property
    def name(self) -> StrStore:
        ...
        