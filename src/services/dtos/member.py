from dataclasses import dataclass

from domain.entities.list import ListEntity
from domain.enums.rank import CommunityRank, MetaRank, ServerRank
from domain.sentinels.unknown import UNKNOWN
from domain.typing.user import UserID
from domain.value_objects.user import UserNameStr


@dataclass(frozen=True, slots=True)
class UserAndMemberInfo:
    user_id: UserID
    name: UserNameStr
    server_rank: ServerRank | UNKNOWN
    meta_rank: MetaRank
    member_info: MemberInfo | None


@dataclass(frozen=True, slots=True)
class MemberInfo:
    community_rank: CommunityRank
    selected_list: ListEntity | None
