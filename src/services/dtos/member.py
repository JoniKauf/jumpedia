from dataclasses import dataclass

from domain.entities.list import ListEntity
from domain.entities.member import MemberEntity
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


@dataclass(frozen=True, slots=True)
class CommunityRankEdited:
    before: MemberEntity
    after: MemberEntity


@dataclass(frozen=True, slots=True)
class SelectedListEdited:
    before: MemberEntity
    after: MemberEntity
    list_after: ListEntity | None
