from dataclasses import dataclass

from domain.enums.rank import CommunityRank
from domain.types.id import ID
from domain.entities.user import UserEntity
from domain.value_objects.community import CommunityName
from domain.value_objects.limits import Limits
from domain.value_objects.string import StrStore


@dataclass(frozen=True, slots=True)
class CreateCommunityDTO:
    name: CommunityName
    limits: Limits
