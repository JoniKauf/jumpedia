from dataclasses import dataclass
import discord as dc

from adapters._base_adapter import BaseAdapter
from adapters._community import CommunityAdapter
from adapters._list._list import ListAdapter
from adapters._jumpedia import JumpediaAdapter
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
    
    def get_or_create_community_user(self, community: CommunityAdapter, override_community_rank: CommunityRank | None = None) -> CommunityUser:
        return community.get_or_create_community_user(self, override_community_rank)
    
    def get_or_create_current_community_user(self, override_community_rank: CommunityRank | None = None) -> CommunityUser:
        return self.jumpedia.get_current_community().get_or_create_community_user(self, override_community_rank)
