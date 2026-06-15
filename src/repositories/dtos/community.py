from dataclasses import dataclass

from domain.value_objects.community import CommunityLimits, CommunityName


@dataclass(frozen=True, slots=True)
class CreateCommunityDTO:
    name: CommunityName
    limits: CommunityLimits
