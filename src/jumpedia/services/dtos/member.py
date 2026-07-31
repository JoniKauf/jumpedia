from dataclasses import dataclass

from jumpedia.domain.entities.list import ListEntity
from jumpedia.domain.entities.member import MemberEntity
from jumpedia.domain.entities.user import UserEntity
from jumpedia.domain.enums.rank import ServerRank
from jumpedia.domain.sentinels.unknown import UNKNOWN


@dataclass(frozen=True, slots=True)
class UserAndMemberInfo:
    user: UserEntity
    server_rank: ServerRank | UNKNOWN
    member_info: MemberInfo | None


@dataclass(frozen=True, slots=True)
class MemberInfo:
    member: MemberEntity
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
