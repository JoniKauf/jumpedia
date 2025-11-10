import typing as t

from src.structures.community import JumpediaUser
from src.structures.user.rank import JumpediaRank

from .. import BaseAdapter

if t.TYPE_CHECKING:
    from .._jumpedia import JumpediaAdapter


class JumpediaUserAdapter(BaseAdapter):
    _jumpedia_user: JumpediaUser

    jumpedia: JumpediaAdapter

    @property
    def name(self) -> str:
        return self._jumpedia_user.user_name

    @property
    def jumpedia_rank(self) -> JumpediaRank:
        return self._jumpedia_user.jumpedia_rank
