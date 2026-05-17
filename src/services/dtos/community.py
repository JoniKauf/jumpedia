


from dataclasses import dataclass

from domain.value_objects.limits import Limits
from domain.value_objects.string import StrStore


@dataclass(frozen=True, slots=True)
class DeletedCommunityDTO:
    name: StrStore
    limits: Limits