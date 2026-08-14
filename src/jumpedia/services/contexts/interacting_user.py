from dataclasses import dataclass

from jumpedia.domain.entities.user import UserEntity
from jumpedia.domain.enums.rank import ServerRank
from jumpedia.domain.typing.server import ServerID


@dataclass(frozen=True, slots=True)
class InteractingUserContext:
    user: UserEntity
    server_rank: ServerRank
    server_id: ServerID
