from adapters import BaseAdapter
from adapters._jumpedia import JumpediaAdapter
from ranks.jumpedia_rank import JumpediaRank
from structures.user.jumpedia_user import JumpediaUser

class JumpediaUserAdapter(BaseAdapter):
    _jumpedia_user: JumpediaUser

    jumpedia: JumpediaAdapter

    @property
    def name(self) -> str:
        return self._jumpedia_user.name
    
    @property
    def jumpedia_rank(self) -> JumpediaRank:
        return self._jumpedia_user.jumpedia_rank