


from dataclasses import dataclass, field
from typing import ClassVar, Self, overload
from adapters._base_adapter import BaseAdapter
from adapters._community import CommunityAdapter
from adapters._users.jumpedia_user import JumpediaUserAdapter
from adapters.interaction import InteractionAdapter
from discordtools import users
from errors.feedback import feedbacks
from ranks.jumpedia_rank import JumpediaRank
from structures.community import Community
from structures.jumpedia import Jumpedia
from utils import text
import discord as dc


def _require_server(server: dc.Guild | None) -> dc.Guild:
    if server is None:
        raise feedbacks.temp("Server is None")
    
    return server

def _require_community_with_name(name: str, jumpedia: Jumpedia) -> Community:
    community = jumpedia.get_community_by_name(name)

    if community is None:
        raise feedbacks.temp(f"Community with the name `{name}` could not be found!")
    
    return community
    
def _require_server_with_community(server: dc.Guild | None, jumpedia: Jumpedia) -> tuple[dc.Guild, Community]:
    server = _require_server(server)
    
    community = jumpedia.get_community_by_server_id(server.id)

    if community is None:
        raise feedbacks.temp("Server not connected to community")
    
    return (server, community)




@dataclass(frozen=True)
class JumpediaAdapter(BaseAdapter):
    _jumpedia: Jumpedia = field(init=False, default=Jumpedia())
    interaction: InteractionAdapter

    # --- Community ---

    def get_communities(self) -> list[CommunityAdapter]:
        return [
            CommunityAdapter(c, self) 
            for c in
            self._jumpedia.get_communities()
        ]
    
    def get_community(self, name: str) -> CommunityAdapter:
        return CommunityAdapter(
            _require_community_with_name(text.sanitize(name), self._jumpedia),
            self
        )
    
    def get_current_community(self) -> CommunityAdapter:
        return CommunityAdapter(
            _require_server_with_community(self.interaction, self._jumpedia)[1],
            self
        )
    
    def create_community(self, name: str, list_name: str) -> CommunityAdapter:
        jumpedia_user = self.get_or_create_current_jumpedia_user()._jumpedia_user
        server_id = _require_server(self._interaction.guild).id

        return CommunityAdapter(self._jumpedia.create_community(
            jumpedia_user=jumpedia_user,
            server_id=server_id,
            name=text.sanitize(name),
            list_name=text.sanitize(list_name)
        ), self)
    
    def delete_community(self, name: str) -> None:
        community = _require_community_with_name(text.sanitize(name), self._jumpedia)

        if not self._jumpedia.delete_community(community):
            raise feedbacks.temp("The community was just deleted!")
        
    def delete_current_community(self) -> None:
        _, community = _require_server_with_community(self._interaction.guild, self._jumpedia)
        self._jumpedia.delete_community(community)
    
    def add_community_to_current_server(self, name: str) -> None:
        server = _require_server(self._interaction.guild)
        community = _require_community_with_name(text.sanitize(name), self._jumpedia)

        self._jumpedia.add_community_to_server(community, server.id)

    def remove_current_community_from_current_server(self) -> None:
        server, community = _require_server_with_community(self._interaction.guild, self._jumpedia)
        self._jumpedia.remove_community_from_server(community, server.id)



    # --- Jumpedia User ---

    def get_or_create_jumpedia_user(self, dc_user: users.AnyDiscordUserT, override_jumpedia_rank: JumpediaRank | None = None) -> JumpediaUserAdapter:
        jumpedia_user = self._jumpedia.create_or_get_jumpedia_user(
            *users.get_user_id_and_name(dc_user),
            override_jumpedia_rank or JumpediaRank.DEFAULT,
            True,
            override_jumpedia_rank is not None
        )

        return JumpediaUserAdapter(jumpedia_user, self)
    
    def get_or_create_current_jumpedia_user(self, override_jumpedia_rank: JumpediaRank | None = None) -> JumpediaUserAdapter:
        return self.get_or_create_jumpedia_user(self._interaction.user, override_jumpedia_rank)

        