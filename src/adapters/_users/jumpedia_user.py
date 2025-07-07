from dataclasses import dataclass
from functools import cached_property
import discord as dc

from adapters._base_adapter import BaseAdapter
from adapters._community import CommunityAdapter
from adapters._list._list import ListAdapter
from adapters._jumpedia import JumpediaAdapter
from adapters._users.community_user import CommunityUserAdapter
from errors.feedback import feedbacks
from ranks.community_rank import CommunityRank
from ranks.jumpedia_rank import JumpediaRank
from ranks.server_rank import ServerRank
from structures.user.community_user import CommunityUser
from structures.user.jumpedia_user import JumpediaUser


@dataclass(frozen=True)
class JumpediaUserAdapter(BaseAdapter):
    _jumpedia_user: JumpediaUser

    jumpedia: JumpediaAdapter

    @property
    def name(self) -> str:
        return self._jumpedia_user.name
    
    @property
    def jumpedia_rank(self) -> JumpediaRank:
        return self._jumpedia_user.jumpedia_rank