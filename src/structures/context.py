from dataclasses import dataclass
from typing import TYPE_CHECKING
import discord as dc
from discordtools import feedbackerrors as fbe

from functools import cached_property

if TYPE_CHECKING:
    from structures.user import CommunityUser, Interactor
    from structures.community import Community
    from structures.jumpedia import Jumpedia
    from structures.list import List
    from structures.ranks import ServerRank

@dataclass(frozen=True)
class Context:
    """A short lived, per-interaction object that gives easy access to
    context regarding the user and other things.
    """

    interaction: dc.Interaction
    
    @cached_property
    def interactor(self) -> 'Interactor':
        from structures.user import Interactor
        return Interactor.create_or_get(self.interaction)

    @cached_property
    def community(self) -> 'Community':
        from structures.jumpedia import Jumpedia
        community = Jumpedia().get_community_by_server_id(self.interaction.guild_id or -1)

        if community is None:
            raise fbe.TemporaryFeedbackError("The server you are on is not connected to a community.")
        
        return community
    
    @cached_property
    def selected_list(self) -> 'List':
        community_user = self.interactor.community_user

        if community_user is not None and (list := community_user.selected_list) is not None:
            return list
        
        if self.community is not None:
            list = self.community.get_default_selected_list()

            if list is not None:
                return list
        
        raise fbe.TemporaryFeedbackError("Neither you, nor the community you are in has a default list selected.")
