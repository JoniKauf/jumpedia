from dataclasses import dataclass

from ranks.jumpedia_rank import JumpediaRank
from ranks.server_rank import ServerRank
from structures import BaseStructure
from structures.jumpedia import Jumpedia


@dataclass(frozen=True, kw_only=True)
class JumpediaUser(BaseStructure):
    __structure_name__ = 'jumpedia user'

    jumpedia: Jumpedia
    id: int
    name: str
    jumpedia_rank: JumpediaRank

    @property
    def identity(self) -> tuple[int, ...]:
        return (self.id, *self.jumpedia.identity)