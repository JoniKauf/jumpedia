from typing import TYPE_CHECKING

from ...ranks.jumpedia_rank import JumpediaRank
from .. import BaseStructure

if TYPE_CHECKING:
    from ..jumpedia import Jumpedia


class JumpediaUser(BaseStructure):
    __structure_name__ = "jumpedia user"

    jumpedia: Jumpedia
    id: int
    user_name: str
    jumpedia_rank: JumpediaRank

    @property
    def identity(self) -> tuple[int, ...]:
        return (self.id, *self.jumpedia.identity)

    @property
    def name(self) -> str:
        return self.user_name
