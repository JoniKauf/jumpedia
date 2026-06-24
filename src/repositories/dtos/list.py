from dataclasses import dataclass

from domain.types.community import CommunityID
from domain.value_objects.string import Str


@dataclass(frozen=True, slots=True)
class ListInsert:
    community_id: CommunityID
    name: Str
