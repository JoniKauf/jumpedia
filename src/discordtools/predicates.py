from typing import Any, Callable, Coroutine, Literal, Optional as Opt
import discord as dc
import discord.app_commands as acmds
import discord.ext.commands as cmds
from discordtools import feedbackerrors as fbe
from ranks import AnyRank
from structure_bridge.context import Context

type AsyncPredicateT = Callable[[dc.Interaction], Coroutine[Any, Any, Literal[True]]]
type PredicateT = Callable[[dc.Interaction], Literal[True]]

def rank_required(required: AnyRank) -> AsyncPredicateT:
    async def predicate_func(ia: dc.Interaction) -> Literal[True]:
        ctx = Context(ia)

        ctx.permitted(required)

        return True
    
    return predicate_func