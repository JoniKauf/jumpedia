from dataclasses import dataclass
from functools import cached_property
import discord as dc
from adapters._base_adapter import BaseAdapter
from adapters._discord.server import ServerAdapter
from adapters._discord.user import UserAdapter
from ranks.server_rank import ServerRank


@dataclass(frozen=True)
class MemberAdapter(BaseAdapter):
    _discord_member: dc.Member

    server: ServerAdapter
    user: UserAdapter

    @cached_property
    def server_rank(self) -> ServerRank:
        if self._discord_member == self.server._server.owner:
            return ServerRank.SERVER_OWNER
        
        if self._discord_member.guild_permissions.administrator:
            return ServerRank.SERVER_ADMINISTRATOR
        
        return ServerRank.SERVER_MEMBER
