from dataclasses import dataclass, field
import discord as dc
from discordtools import feedbackerrors as fbe

from functools import cached_property
from structures.user import User
from structures.community import Community
from structures.jumpedia import Jumpedia
from structures.list import List

@dataclass(frozen=True, slots=True)
class Context:
    """A short lived, per-interaction object that gives easy access to
    context regarding the user and other things.
    """

    interaction: dc.Interaction
    
    @cached_property
    def user(self) -> User:
        return User.get_actor(self)
    
    @cached_property
    def community(self) -> Community:
        return Jumpedia().get_community_by_guild_id(self.interaction.guild_id or -1)
    
    @cached_property
    def list(self) -> List:
        if (list := self.user.selected_list) is not None:
            return list
        
        raise fbe.TemporaryFeedbackError("No list selected")
