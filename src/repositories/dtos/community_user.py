from dataclasses import dataclass

from domain.entities.user import UserEntity
from domain.enums.rank import CommunityRank
from domain.types.community import CommunityID
from domain.types.list import ListID


@dataclass(frozen=True, slots=True)
class CreateCommunityUserDTO:
    user: UserEntity
    community_id: CommunityID
    rank: CommunityRank = CommunityRank.DEFAULT
    selected_list_id: ListID | None = None
