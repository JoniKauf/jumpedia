
from dataclasses import dataclass

from domain.value_objects.strings import StrStore

@dataclass(frozen=True, unsafe_hash=True, slots=True)
class ListEntity:
    list_id: int
    community_id: int
    name: StrStore
    

