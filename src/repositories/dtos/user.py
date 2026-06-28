from dataclasses import dataclass

from domain.enums.rank import MetaRank
from domain.types.user import UserID
from domain.value_objects.user import UserNameStr


@dataclass(frozen=True, slots=True)
class UserInsert:
    id: UserID
    name: UserNameStr
    rank: MetaRank = MetaRank.DEFAULT
