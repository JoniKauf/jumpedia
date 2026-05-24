from dataclasses import dataclass

from domain.entities.user import UserEntity
from domain.enums.rank import ServerRank
from domain.value_objects.string import StrStore


@dataclass(frozen=True, slots=True)
class InteractingUserContext:
    id: int
    name: StrStore
    server_rank: ServerRank
    server_id: int
