from typing import Any, Callable, Coroutine, Literal, Optional as Opt
import discord as dc
import discord.app_commands as acmds
import discord.ext.commands as cmds
from discordtools import feedbackerrors as fbe

from structures.context import Context
from structures.ranks import AnyRank, MetaRank, ServerRank, CommunityRank

type AsyncPredicateT = Callable[[dc.Interaction], Coroutine[Any, Any, Literal[True]]]
type PredicateT = Callable[[dc.Interaction], Literal[True]]

def in_guild(guild: dc.Guild | int | None) -> PredicateT:
    guild = guild if isinstance(guild, int) or guild is None else guild.id

    def predicate_func(ia: dc.Interaction) -> Literal[True]:
        if guild is None:
            if ia.guild_id is not None:
                return True
        elif ia.guild_id == guild:
            return True
        
        raise fbe.TemporaryFeedbackError(f"Not in guild {guild}" if guild is not None else "Not in any guild")

    return predicate_func


def rank_required(rank_required: AnyRank) -> AsyncPredicateT:
    async def predicate_func(ia: dc.Interaction) -> Literal[True]:
        actor = Context(ia).interactor

        if actor.permitted(rank_required):
            return True
        
        if isinstance(rank_required, MetaRank):
            rank = actor.meta_rank
        elif isinstance(rank_required, CommunityRank):
            rank = actor.community_rank
        else:
            rank = actor.server_rank

        raise fbe.TemporaryFeedbackError(f"Your rank is '{rank}' but you must at least be {rank_required}") 

    return predicate_func