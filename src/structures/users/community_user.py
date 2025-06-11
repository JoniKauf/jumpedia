


from dataclasses import dataclass

from ranks.community_rank import CommunityRank
from ranks.meta_rank import MetaRank
from structures.abstract_structure import StructureBase
from structures.community.community import Community
from structures.list.list import List
from structures.users.meta_user import MetaUser


@dataclass(frozen=True, kw_only=True)
class CommunityUser(StructureBase):
    meta_user: MetaUser
    community: 'Community'
    community_rank: CommunityRank
    selected_list: 'List | None'
    
    @property
    def meta_rank(self) -> MetaRank:
        return self.meta_user.meta_rank
    
    @property
    def identity(self) -> tuple[int, ...]:
        return (*self.meta_user.identity, self.community.id)
    
    @property
    def most_important_rank(self) -> CommunityRank | MetaRank:
        return self.meta_rank or self.community_rank
    
    @property
    def parent(self) -> Community:
        return self.community

