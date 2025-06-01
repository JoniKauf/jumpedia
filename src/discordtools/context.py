from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal
import discord as dc
from discordtools import feedbackerrors as fbe, helpers, required

from functools import cached_property

from structures.users import CommunityUser, MetaUser, ServerUser
from structures.community import Community
from structures.jumpedia import Jumpedia
from structures.list import List
from structures.ranks import AnyRank, CommunityRank, MetaRank, ServerRank

@dataclass(frozen=True)
class Context:
    """A short lived, per-interaction object that gives easy access to
    context regarding the user and other things.
    """

    interaction: dc.Interaction
    
    @cached_property
    def server(self) -> dc.Guild:
        return required.server(self.interaction.guild)
    
    @cached_property
    def jumpedia(self) -> Jumpedia:
        from structures.jumpedia import Jumpedia
        return Jumpedia()
    
    @cached_property
    def community(self) -> Community:
        return required.community(
            self.community_opt
        )
    
    @cached_property
    def community_opt(self) -> Community | None:
        return self.jumpedia.get_community_by_server_id(self.server.id)
        
    @cached_property
    def meta_user(self) -> MetaUser:
        user = self.interaction.user
        return self.jumpedia.create_or_get_user(user.id, user.name)
    
    @cached_property
    def community_user(self) -> CommunityUser:
        return self.community.create_or_get_community_user(self.interaction.user.id, self.user_name)
    
    @cached_property
    def community_user_opt(self) -> CommunityUser | None:
        community = self.community_opt

        if community is None:
            return None
        
        return self.community_user

    @cached_property
    def server_user(self) -> ServerUser:
        return ServerUser(
            community_user=self.community_user,
            server_rank=ServerRank.get_from_discord_user(self.interaction.user)
        )
    
    @cached_property
    def selected_list(self) -> List:
        community_user = self.server_user.community_user

        if community_user is not None and (list := community_user.selected_list) is not None:
            return list
        
        if self.community is not None:
            list = self.community.get_default_selected_list()

            if list is not None:
                return list
        
        raise fbe.TemporaryFeedbackError("Neither you, nor the community you are in has a default list selected.")

    @cached_property
    def user_name(self) -> str:
        return helpers.get_user_name(self.interaction.user)
    
    def permitted(self, required: AnyRank) -> None:
        if isinstance(required, MetaRank):
            if self.meta_user.meta_rank >= required:
                return
            
            raise fbe.TemporaryFeedbackError(f"You must at least have the meta rank {required}")

        # Any meta rank is better than the other 2 ranks, so if one is given
        # we are successful
        if self.meta_user.meta_rank > MetaRank.NONE:
            return
        
        if isinstance(required, CommunityRank):
            if self.community_user.community_rank >= required:
                return
            
            raise fbe.TemporaryFeedbackError(f"You must at least have the community rank {required}")
            
        if self.server_user.server_rank >= required:
            return
        
        raise fbe.TemporaryFeedbackError(f"You must at least have the server rank {required}")

