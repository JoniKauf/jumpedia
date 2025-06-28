


from dataclasses import dataclass, field
from typing import ClassVar, Self
from adapters.base_adapter import BaseAdapter
from adapters.community_adapter import _CommunityAdapter
from adapters.user_adapter import _UserAdapter
from discordtools import users
from ranks.jumpedia_rank import JumpediaRank
from structures.community import Community
from structures.jumpedia import Jumpedia
from utils import required, text
import discord as dc

@dataclass(frozen=True)
class JumpediaAdapter(BaseAdapter[Jumpedia]):
    _structure: Jumpedia = field(init=False, default=Jumpedia())

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
    
    def get_user(self, user: users.AnyDiscordUserT) -> _UserAdapter:
        return _UserAdapter(self._interaction, self._structure.get_or_create_user(
            *users.get_user_id_and_name(user),
            JumpediaRank.DEFAULT,
            True,
            False
        ))
    
    def a(self):
        self._structure.create_community()