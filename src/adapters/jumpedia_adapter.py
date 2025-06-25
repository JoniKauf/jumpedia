


from dataclasses import dataclass
from typing import ClassVar, Self
from adapters.base_adapter import BaseAdapter
from adapters.community_adapter import _CommunityAdapter
from structures.community import Community
from structures.jumpedia import Jumpedia
from utils import required, text
import discord as dc

@dataclass(frozen=True)
class JumpediaAdapter(BaseAdapter[Jumpedia]):
    def get_communities(self) -> list[_CommunityAdapter]:
        return [
            _CommunityAdapter(self._interaction, c) 
            for c in
            self._structure.get_communities()
        ]
    
    def get_current_community(self) -> _CommunityAdapter:
        server = required.server_not_none(self._interaction.guild)

        community = self._structure.get_community_by_server_id(server.id)
        
        return _CommunityAdapter(
            self._interaction, 
            required.server_with_community(community)
        )
    
    def get_community_by_name(self, name: str) -> _CommunityAdapter:
        name = text.sanitize(name)

        community = self._structure.get_community_by_name(name)

        return _CommunityAdapter(
            self._interaction, 
            required.structure_not_none(community, Community, name)
        )