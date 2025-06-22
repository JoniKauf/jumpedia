


from dataclasses import dataclass
from adapters.base_adapter import BaseAdapter
from adapters.community_adapter import CommunityAdapter
from structures.community import Community
from structures.meta import Meta
from utils import required, text
import discord as dc

@dataclass(frozen=True)
class JumpediaAdapter(BaseAdapter[Meta]):
    
    def get_communities(self) -> list[CommunityAdapter]:
        return [
            CommunityAdapter(self.context, c) 
            for c in
            self._structure.get_communities()
        ]
    
    def get_current_community(self) -> CommunityAdapter:
        server = required.server_not_none(self.context.interaction.guild)

        community = self._structure.get_community_by_server_id(server.id)
        
        return CommunityAdapter(
            self.context, 
            required.server_with_community(community)
        )
    
    def get_community_by_name(self, name: str) -> CommunityAdapter:
        name = text.sanitize(name)

        community = self._structure.get_community_by_name(name)

        return CommunityAdapter(
            self.context, 
            required.structure_not_none(community, Community, name)
        )