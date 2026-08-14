from jumpedia.domain.entities.base import BaseEntity
from jumpedia.domain.entities.user import UserEntity

lazy from jumpedia.domain.enums.rank import CommunityRank
lazy from jumpedia.domain.typing.community import CommunityID
lazy from jumpedia.domain.typing.list import ListID
from jumpedia.domain.typing.member import MemberID

lazy from jumpedia.domain.value_objects.user import UserNameStr
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
