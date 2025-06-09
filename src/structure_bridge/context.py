from dataclasses import dataclass
import discord as dc
from discord_structures import feedbackerrors as fbe, required, utils

from functools import cached_property

from structures.community.community import Community
from structures.jumpedia.jumpedia import Jumpedia
from structures.list.list import List
from structures.ranks.server_rank import ServerRank
from structures.users.community_user import CommunityUser
from structures.users.server_user import ServerUser

@dataclass(frozen=True)
class Context:
    """A short lived, per-interaction object that gives easy access to
    context regarding the user and other things.
    """

    interaction: dc.Interaction
    
    @cached_property
    def server(self) -> dc.Guild:
        return required.server_generic(self.interaction.guild)
    
    @cached_property
    def jumpedia(self) -> Jumpedia:
        from structures.jumpedia.jumpedia import Jumpedia
        return Jumpedia()
    
    @cached_property
    def community(self) -> Community:
        return required.server_with_community(
            self.jumpedia.get_community_by_server_id(self.server.id)
        )    
    
    @cached_property
    def community_opt(self) -> Community | None:
        return 
        
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
        return utils.get_user_name(self.interaction.user)
    
    def get_selected_list(self, explicit_list: str | None) -> List:
        if explicit_list is None:
            return self.selected_list
        
        return required.structure_name_not_found(
            self.community.get_list_by_name(explicit_list),
            explicit_list,
            List
        )
        
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

