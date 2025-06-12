from dataclasses import dataclass, field
import functools
import types
from typing import Any, Callable, Literal
import discord as dc
from discordtools import feedbackerrors as fbe, required, utils

from ranks import AnyRank
from ranks.community_rank import CommunityRank
from ranks.meta_rank import MetaRank
from ranks.server_rank import ServerRank
from structures.community.community import Community
from structures.jumpedia.jumpedia import Jumpedia
from structures.list.list import List
from structures.users.community_user import CommunityUser
from structures.users.meta_user import MetaUser
from structures.users.server_user import ServerUser


def optimized_no_arg_method_cache[T](func: Callable[['Context'], T]) -> Callable[['Context'], T]:

    @functools.wraps(func)
    def wrapper(self: Context) -> T:
        return self._cache.setdefault(func.__name__, func(self))

    return wrapper


@dataclass(frozen=True)
class Context:
    """A short lived, per-interaction object that gives easy access to
    context regarding the user and other things.
    """

    interaction: dc.Interaction
    _cache: dict[str, Any] = field(init=False, default_factory=dict)

    @optimized_no_arg_method_cache
    def get_server(self) -> dc.Guild:
        return required.user_on_server(self.interaction.user)
    
    @optimized_no_arg_method_cache
    def get_jumpedia(self) -> Jumpedia:
        return Jumpedia()
    
    @optimized_no_arg_method_cache
    def get_community(self) -> Community:
        return required.server_with_community(
            self.get_jumpedia().get_community_by_server_id(self.get_server().id)
        )    

    @optimized_no_arg_method_cache
    def get_meta_user(self) -> MetaUser:
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
    def get_selected_list(self) -> List:
        community_user = self.get_server_user().community_user

        if community_user is not None and (list := community_user.selected_list) is not None:
            return list
        
        if (community := self.get_community()) is not None:
            list = community.get_default_selected_list()

            if list is not None:
                return list
        
        raise fbe.TemporaryFeedbackError("Neither you, nor the community you are in has a default list selected.")

    @optimized_no_arg_method_cache
    def get_user_name(self) -> str:
        return utils.get_user_name(self.interaction.user)
    
    @functools.lru_cache
    def get_explicit_or_selected_list(self, explicit_list_name: str | None = None) -> List:
        if explicit_list_name is None:
            return self.get_selected_list()
        
        return required.structure_with_name(
            self.get_community().get_list_by_name(explicit_list_name),
            explicit_list_name,
            List
        )
    
    @functools.lru_cache
    def permitted(self, required: AnyRank) -> None:
        if isinstance(required, MetaRank):
            if self.get_meta_user().meta_rank >= required:
                return
            
            raise fbe.TemporaryFeedbackError(f"You must at least have the meta rank {required}")

        # Any meta rank is better than the other 2 ranks, so if one is given
        # we are successful
        if self.get_meta_user().meta_rank > MetaRank.NONE:
            return
        
        if isinstance(required, CommunityRank):
            if self.get_community_user().community_rank >= required:
                return
            
            raise fbe.TemporaryFeedbackError(f"You must at least have the community rank {required}")
            
        if self.get_server_user().server_rank >= required:
            return
        
        raise fbe.TemporaryFeedbackError(f"You must at least have the server rank {required}")

