from domain.entities.base import BaseEntity
from domain.entities.user import UserEntity

lazy from domain.enums.rank import CommunityRank
lazy from domain.typing.community import CommunityID
lazy from domain.typing.list import ListID
from domain.typing.member import MemberID

lazy from domain.value_objects.user import UserNameStr
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MemberEntity(BaseEntity[MemberID]):
    user: UserEntity
    community_id: CommunityID
    community_rank: CommunityRank = CommunityRank.DEFAULT
    selected_list_id: ListID | None = None

    @property
    def member_id(self) -> MemberID:
        return self.key[0]

    @property
    def name(self) -> UserNameStr:
        return self.user.name
