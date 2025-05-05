from dataclasses import dataclass
import discord as dc

from people.user import User
from structures.community import Community
from structures.jumpedia import Jumpedia
from structures.list import List

@dataclass(frozen=True, slots=True)
class Context:
    interaction: dc.Interaction
    
    @property
    def community(self) -> Community:
        return Jumpedia().get_community_by_guild_id(self.interaction.guild_id or -1)