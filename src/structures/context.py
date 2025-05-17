from dataclasses import dataclass
from typing import TYPE_CHECKING
import discord as dc
from discordtools import feedbackerrors as fbe

from functools import cached_property

if TYPE_CHECKING:
    from structures.user import User
    from structures.community import Community
    from structures.jumpedia import Jumpedia
    from structures.list import List
    from structures.ranks import GuildRank

@dataclass(frozen=True)
class Context:
    """A short lived, per-interaction object that gives easy access to
    context regarding the user and other things.
    """

    ia: dc.Interaction
    
    @cached_property
    def user(self) -> 'User':
        from structures.user import User
        return User.get_actor(self)
    
    @cached_property
    def guild_rank(self) -> 'GuildRank':
        from structures.ranks import GuildRank
        return GuildRank.get_from_discord_user(self.ia.user)

    @cached_property
    def community(self) -> 'Community | None':
        from structures.jumpedia import Jumpedia
        return Jumpedia().get_community_by_guild_id(self.ia.guild_id or -1)
    
    @cached_property
    def list(self) -> 'List':
        if (list := self.user.selected_list) is not None:
            return list
        
        if self.community is not None:
            list = self.community.get_default_selected_list()

            if list is not None:
                return list
        
        raise fbe.TemporaryFeedbackError("Neither you, nor the community you are in has a default list selected.")
