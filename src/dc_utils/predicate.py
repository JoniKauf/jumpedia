import typing as t
from types import CoroutineType

import discord as dc

from domain.rank import AnyRankT

from . import user

type AsyncPredicateT = t.Callable[
    [dc.Interaction], CoroutineType[t.Any, t.Any, t.Literal[True]]
]
type PredicateT = t.Callable[[dc.Interaction], t.Literal[True]]


def rank_required(
    rank_required: AnyRankT, /, *ranks_required: AnyRankT
) -> AsyncPredicateT:
    async def predicate(interaction: dc.Interaction) -> t.Literal[True]:
        user.validate_allowed(interaction, rank_required, *ranks_required)
        return True

    return predicate
