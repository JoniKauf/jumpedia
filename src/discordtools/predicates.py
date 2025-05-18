from typing import Any, Callable, Coroutine, Literal, Optional as Opt
import discord as dc
import discord.app_commands as acmds
import discord.ext.commands as cmds
from discordtools import feedbackerrors as fbe

from structures.context import Context
from structures.ranks import GuildRank, UserRank

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


def user_rank(
    min_required: UserRank = UserRank.HIGHEST
) -> AsyncPredicateT:
    async def predicate_func(ia: dc.Interaction) -> Literal[True]:
        try:
            user_rank = Context(ia).actor.user_rank
        except fbe.TemporaryFeedbackError:
            user_rank = UserRank.DEFAULT

        if user_rank.permitted(min_required):
            return True
        
        raise fbe.TemporaryFeedbackError(f"Your user rank is {user_rank} but you must at least be {min_required}") 

    return predicate_func


def guild_rank(
    min_required: GuildRank = GuildRank.HIGHEST
) -> AsyncPredicateT:
    async def predicate_func(ia: dc.Interaction) -> Literal[True]:
        ctx = Context(ia)

        if (guild_rank := ctx.guild_rank).permitted(ctx.actor.user_rank, min_required):
            return True
        
        raise fbe.TemporaryFeedbackError(f"Your server rank is {guild_rank} but you must at least be {min_required}")

    return predicate_func