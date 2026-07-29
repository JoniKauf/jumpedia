from dataclasses import dataclass

from domain.entities.user import UserEntity
from domain.enums.rank import CommunityRank
from domain.typing.community import CommunityID
from domain.typing.list import ListID


@dataclass(frozen=True, slots=True)
class MemberInsert:
    user: UserEntity
    community_id: CommunityID
    community_rank: CommunityRank = CommunityRank.DEFAULT
    selected_list_id: ListID | None = None
