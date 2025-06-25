from dataclasses import dataclass, field
import functools
import types
from typing import Any, Callable, Literal
import discord as dc
from adapters.community_adapter import _CommunityAdapter
from adapters.jumpedia_adapter import JumpediaAdapter
from utils import functools2, required

from ranks import AnyRank
from ranks.community_rank import CommunityRank
from ranks.jumpedia_rank import JumpediaRank
from ranks.server_rank import ServerRank
from structures.community import Community
from structures.jumpedia import Jumpedia
from structures.list import List
from structures.user.community_user import CommunityUser
from structures.user.jumpedia_user import JumpediaUser
from structures.user.server_user import ServerUser





@dataclass(frozen=True)
class Context:
    """A short lived, per-interaction object that gives easy access to
    context regarding the user and other things.
    """

    interaction: dc.Interaction
    _cache: dict[str, Any] = field(init=False, default_factory=dict)

    
    
    @functools2.optimized_no_arg_method_cache
    def get_community(self) -> _CommunityAdapter:
        return required.server_with_community(
            self.get_jumpedia().get_community_by_server_id(self.get_server().id)
        )    

    @optimized_no_arg_method_cache
    def get_meta_user(self) -> JumpediaUser:
        user = self.interaction.user
        return self.get_jumpedia().create_or_get_user(user.id, user.name)
    
    @optimized_no_arg_method_cache
    def get_community_user(self) -> CommunityUser:
        return self.get_community().create_or_get_community_user(self.interaction.user.id, self.get_user_name())

    @optimized_no_arg_method_cache
    def get_server_user(self) -> ServerUser:
        return ServerUser(
            community_user=self.get_community_user(),
            server_rank=ServerRank.get_from_discord_user(self.interaction.user)
        )
    
    

    @optimized_no_arg_method_cache
    def get_user_name(self) -> str:
        return user.get_user_name(self.interaction.user)
    
    @functools.lru_cache
    def get_explicit_or_selected_list(self, explicit_list_name: str | None = None) -> List:
        if explicit_list_name is None:
            return self.get_selected_list()
        
        return required.structure_not_none(
            self.get_community().get_list_by_name(explicit_list_name),
            explicit_list_name,
            List
        )
    
    @functools.lru_cache
    def permitted(self, required: AnyRank) -> None:
        if isinstance(required, JumpediaRank):
            if self.get_meta_user().jumpedia_rank >= required:
                return
            
            raise fbe.TemporaryFeedbackError(f"You must at least have the meta rank {required}")

        # Any meta rank is better than the other 2 ranks, so if one is given
        # we are successful
        if self.get_meta_user().jumpedia_rank > JumpediaRank.NONE:
            return
        
        if isinstance(required, CommunityRank):
            if self.get_community_user().community_rank >= required:
                return
            
            raise fbe.TemporaryFeedbackError(f"You must at least have the community rank {required}")
            
        if self.get_server_user().server_rank >= required:
            return
        
        raise fbe.TemporaryFeedbackError(f"You must at least have the server rank {required}")

    @functools.lru_cache
    def get_list_by_name(self, name: str) -> 