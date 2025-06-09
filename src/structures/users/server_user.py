


from dataclasses import dataclass

from structures.ranks.community_rank import CommunityRank
from structures.ranks.meta_rank import MetaRank
from structures.ranks.server_rank import ServerRank
from structures.users.community_user import CommunityUser
from structures.users.meta_user import MetaUser


@dataclass(frozen=True, kw_only=True)
class ServerUser:
    community_user: CommunityUser
    server_rank: ServerRank

    @property
    def meta_user(self) -> MetaUser:
        return self.community_user.meta_user
    
    @property
    def meta_rank(self) -> MetaRank:
        return self.community_user.meta_rank
    
    @property
    def community_rank(self) -> CommunityRank:
        return self.community_user.community_rank
    
    @property
    def identity(self) -> tuple[int, ...]:
        return self.meta_user.identity
    
    def __hash__(self) -> int:
        return hash(self.identity)
    
    def __eq__(self, value: object) -> bool:
        return isinstance(value, self.__class__) and self.identity == value.identity