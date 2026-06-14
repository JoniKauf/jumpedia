from dataclasses import dataclass

from domain.enums.rank import MetaRank
from domain.types.user import UserID
from domain.value_objects.user import UserName


@dataclass(frozen=True, slots=True)
class CreateUserDTO:
    id: UserID
    name: UserName
    rank: MetaRank = MetaRank.DEFAULT
