from jumpedia.domain.entities.base import BaseEntity
from jumpedia.domain.enums.rank import MetaRank
from jumpedia.domain.typing.user import UserID

lazy from jumpedia.domain.value_objects.user import UserNameStr
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class UserEntity(BaseEntity[UserID]):
    name: UserNameStr
    meta_rank: MetaRank = MetaRank.DEFAULT

    @property
    def user_id(self) -> UserID:
        return self.key[0]
