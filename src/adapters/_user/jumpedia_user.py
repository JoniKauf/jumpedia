import typing as t

from ...ranks.jumpedia_rank import JumpediaRank
from ...structures.user.jumpedia_user import JumpediaUser
from .. import BaseAdapter

if t.TYPE_CHECKING:
    from .._jumpedia import JumpediaAdapter


class JumpediaUserAdapter(BaseAdapter):
    _jumpedia_user: JumpediaUser

    jumpedia: JumpediaAdapter

    @property
    def name(self) -> str:
        return self._jumpedia_user.name

    @property
    def jumpedia_rank(self) -> JumpediaRank:
        return self._jumpedia_user.jumpedia_rank
