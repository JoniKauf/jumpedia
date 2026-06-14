from dataclasses import dataclass

from domain.types.community import CommunityID
from domain.value_objects.string import StrStore


@dataclass(frozen=True, slots=True)
class CreateListDTO:
    community_id: CommunityID
    name: StrStore
