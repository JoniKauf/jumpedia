from dataclasses import dataclass

from domain.types.id import ID
from domain.value_objects.string import StrStore


@dataclass(frozen=True, slots=True)
class CreateListDTO:
    community_id: ID
    name: StrStore
