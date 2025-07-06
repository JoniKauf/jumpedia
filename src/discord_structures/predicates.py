from typing import Any, Callable, Coroutine, Literal, Optional as Opt, assert_never
import discord as dc
import discord.app_commands as acmds
import discord.ext.commands as cmds
from adapters.interaction import InteractionAdapter
from errors.feedback import FeedbackError, feedbacks
from errors import ImpossibleError
from ranks import AnyRankT
from ranks.community_rank import CommunityRank
from ranks.jumpedia_rank import JumpediaRank
from ranks.server_rank import ServerRank
import discordtools.messaging as msg

type AsyncPredicateT = Callable[[dc.Interaction], Coroutine[Any, Any, Literal[True]]]
type PredicateT = Callable[[dc.Interaction], Literal[True]]

def _not_permitted[T: AnyRankT](my_rank: T, rank_required: T) -> FeedbackError:
    return FeedbackError(
        "Not Permitted",
        f"You must at least have the rank {msg.code(my_rank)}, but your rank is only {msg.code(rank_required)}!"
    )

def rank_required(rank_required: AnyRankT) -> AsyncPredicateT:
    async def predicate_func(interaction: dc.Interaction) -> Literal[True]:
        # Power == 0 required
        if not rank_required:
            return True
        
        jumpedia_user = InteractionAdapter(interaction).jumpedia.get_or_create_current_jumpedia_user()
        jumpedia_rank = jumpedia_user.jumpedia_rank

        if isinstance(rank_required, JumpediaRank):
            if jumpedia_rank >= rank_required:
                return True
            
            raise _not_permitted(jumpedia_rank, rank_required)
        
        if isinstance(rank_required, ServerRank):
            if jumpedia_rank:
                return True
            
            server_rank = InteractionAdapter(interaction).server_rank

            if server_rank >= rank_required:
                return True
            
            raise _not_permitted(server_rank, rank_required)
        
        if isinstance(rank_required, CommunityRank):
            if jumpedia_rank:
                return True
            
            community_rank = jumpedia_user.get_or_create_current_community_user().community_rank

            if community_rank >= rank_required:
                return True
            
            raise _not_permitted(community_rank, rank_required)
        
        assert_never(rank_required)
    
    return predicate_func