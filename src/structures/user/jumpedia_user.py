from dataclasses import dataclass
import discord as dc

from ranks.jumpedia_rank import JumpediaRank
from ranks.server_rank import ServerRank
from structures.base_structure import BaseStructure
from structures.jumpedia import Jumpedia


@dataclass(frozen=True, kw_only=True)
class JumpediaUser(BaseStructure):
    __structure_name__ = 'jumpedia user'

    jumpedia: Jumpedia
    id: int
    name: str
    jumpedia_rank: JumpediaRank

    @property
    def identity(self) -> tuple[int, ...]:
        return (self.id, *self.jumpedia.identity)
    
    def get_server_rank(self, discord_user: dc.User | dc.Member) -> ServerRank | None:
        if isinstance(discord_user, dc.User):
            return None
        
        if discord_user.id == discord_user.guild.owner_id:
            return ServerRank.SERVER_OWNER
        
        if discord_user.guild_permissions.administrator:
            return ServerRank.SERVER_ADMINISTRATOR
        
        return ServerRank.MEMBER