
from dataclasses import dataclass

from domain.value_objects.limits import Limits
from domain.value_objects.strings import StrStore

@dataclass(frozen=True, unsafe_hash=True, slots=True)
class CommunityEntity:
    community_id: int
    name: StrStore
    limits: Limits
    