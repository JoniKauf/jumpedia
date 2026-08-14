from dataclasses import dataclass

from jumpedia.domain.entities.user import UserEntity
from jumpedia.domain.enums.rank import CommunityRank
from jumpedia.domain.typing.community import CommunityID
from jumpedia.domain.typing.list import ListID


@dataclass(frozen=True, slots=True)
class MemberInsert:
    user: UserEntity
    community_id: CommunityID
    community_rank: CommunityRank = CommunityRank.DEFAULT
    selected_list_id: ListID | None = None
