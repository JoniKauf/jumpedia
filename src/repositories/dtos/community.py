from dataclasses import dataclass

from domain.value_objects.community import CommunityLimits, CommunityNameStr


@dataclass(frozen=True, slots=True)
class CommunityInsert:
    name: CommunityNameStr
    limits: CommunityLimits
