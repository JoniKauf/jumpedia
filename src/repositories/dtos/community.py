from dataclasses import dataclass

from domain.value_objects.community import CommunityName
from domain.value_objects.community import CommunityLimits


@dataclass(frozen=True, slots=True)
class CreateCommunityDTO:
    name: CommunityName
    limits: CommunityLimits
