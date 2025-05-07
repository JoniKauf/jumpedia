from typing import Any, Callable, Coroutine, Optional as Opt
import discord as dc
import discord.app_commands as acmds
import discord.ext.commands as cmds
from discordtools import feedbackerrors as fbe

from structures import ranks

type PredicateT = Callable[[dc.Interaction], Coroutine[Any, Any, bool]]

def multiple_all(predicate: PredicateT, *predicates: PredicateT) -> PredicateT:
    preds = (predicate,) + predicates

    async def predicate_func(ia: dc.Interaction) -> bool:
        for pred in preds:
            if not await pred(ia):
                return False
        
        return True
    
    return predicate_func


def multiple_any(predicate: PredicateT, *predicates: PredicateT) -> PredicateT:
    preds = (predicate,) + predicates

    async def predicate_func(ia: dc.Interaction) -> bool:
        for pred in preds:
            if await pred(ia):
                return True
        
        return False
    
    return predicate_func


def permission(
    min_user_rank: ranks.UserRank = ranks.USER_RANKS.USER, 
    min_server_rank: ranks.ServerRank = ranks.SERVER_RANKS.MEMBER
) -> PredicateT:
    async def predicate_func(ia: dc.Interaction) -> bool:
        return ranks.permitted(ia, min_user_rank, min_server_rank)

    return predicate_func