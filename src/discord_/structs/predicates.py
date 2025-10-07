import typing as t

import discord as dc

from ...adapters.interaction import InteractionAdapter
from ...errors.feedback import FeedbackError
from ...ranks import AnyRankT
from ...ranks.community_rank import CommunityRank
from ...ranks.jumpedia_rank import JumpediaRank
from ...ranks.server_rank import ServerRank

type AsyncPredicateT = t.Callable[
    [dc.Interaction], t.Coroutine[t.Any, t.Any, t.Literal[True]]
]
type PredicateT = t.Callable[[dc.Interaction], t.Literal[True]]


def _not_permitted[T: AnyRankT](my_rank: T, rank_required: T) -> FeedbackError:
    return FeedbackError(
        "Not Permitted",
        f"You must at least have the rank `{rank_required}`, but your rank is only `{my_rank}`!",
    )


def rank_required(rank_required: AnyRankT) -> AsyncPredicateT:
    async def predicate_func(interaction: dc.Interaction) -> t.Literal[True]:
        # Power == 0 required
        if not rank_required:
            return True

        jumpedia = InteractionAdapter(interaction).jumpedia
        jumpedia_user = jumpedia.get_or_create_current_jumpedia_user()
        jumpedia_rank = jumpedia_user.jumpedia_rank

        if isinstance(rank_required, JumpediaRank):
            if jumpedia_rank >= rank_required:
                return True

            raise _not_permitted(jumpedia_rank, rank_required)

        if isinstance(rank_required, ServerRank):
            if jumpedia_rank:
                return True

            server_rank = InteractionAdapter(interaction).current_member.server_rank

            if server_rank >= rank_required:
                return True

            raise _not_permitted(server_rank, rank_required)

        if isinstance(rank_required, CommunityRank):
            if jumpedia_rank:
                return True

            community_rank = (
                jumpedia.get_current_community()
                .get_or_create_community_user(jumpedia_user)
                .community_rank
            )

            if community_rank >= rank_required:
                return True

            raise _not_permitted(community_rank, rank_required)

        t.assert_never(rank_required)

    return predicate_func
