from jumpedia.domain.entities.user import UserEntity
from jumpedia.domain.enums.rank import MetaRank
from jumpedia.domain.typing.user import UserID
from jumpedia.domain.value_objects.attribute import dataclass
from jumpedia.domain.value_objects.user import UserNameStr


@dataclass(frozen=True, slots=True)
class UserRef:
    id: UserID
    name: UserNameStr


@dataclass(frozen=True, slots=True)
class MetaRankEdited:
    before: UserEntity
    after: UserEntity
