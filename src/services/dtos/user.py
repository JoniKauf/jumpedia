from domain.entities.user import UserEntity
from domain.enums.rank import MetaRank
from domain.typing.user import UserID
from domain.value_objects.attribute import dataclass
from domain.value_objects.user import UserNameStr


@dataclass(frozen=True, slots=True)
class UserRef:
    id: UserID
    name: UserNameStr


@dataclass(frozen=True, slots=True)
class MetaRankEdited:
    before: UserEntity
    after: UserEntity
