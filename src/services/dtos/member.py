from dataclasses import dataclass

from domain.entities.list import ListEntity
from domain.entities.member import MemberEntity
from domain.entities.user import UserEntity
from domain.enums.rank import ServerRank
from domain.sentinels.unknown import UNKNOWN


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
