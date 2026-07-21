from dataclasses import dataclass

from domain.entities.user import UserEntity
from domain.enums.rank import ServerRank
from domain.typing.server import ServerID


@dataclass(frozen=True, slots=True)
class InteractingUserContext:
    user: UserEntity
    server_rank: ServerRank
    server_id: ServerID
