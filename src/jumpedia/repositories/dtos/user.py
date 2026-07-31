from dataclasses import dataclass

from jumpedia.domain.enums.rank import MetaRank
from jumpedia.domain.typing.user import UserID
from jumpedia.domain.value_objects.user import UserNameStr


@dataclass(frozen=True, slots=True)
class UserInsert:
    id: UserID
    name: UserNameStr
    meta_rank: MetaRank = MetaRank.DEFAULT
