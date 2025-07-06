from dataclasses import dataclass
from functools import cached_property
from adapters._base_adapter import BaseAdapter
import discord as dc

from adapters._users.discord_user import DiscordUserAdapter
from errors.feedback import feedbacks
from ranks.server_rank import ServerRank


@dataclass(frozen=True)
class DiscordServerAdapter(BaseAdapter):
    _server: dc.Guild
    _current_member: dc.Member

    @property
    def id(self) -> int:
        return self._server.id
    
    def get_current_discord_member_server_rank(self) -> ServerRank:
        if self._current_member == self._server.owner:
            return ServerRank.SERVER_OWNER
        
        if self._current_member.guild_permissions.administrator:
            return ServerRank.SERVER_ADMINISTRATOR
        
        return ServerRank.SERVER_MEMBER