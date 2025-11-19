import typing as t
from types import CoroutineType

import discord as dc

from adapters._jumpedia import JumpediaAdapter
from adapters._user import JumpediaUserAdapter
from adapters.interaction import InteractionAdapter
from discord_.errors import FeedbackError
from structures.community import CommunityRank
from utils.rank import AnyRankT, JumpediaRank, ServerRank

type AsyncPredicateT = t.Callable[
    [dc.Interaction], CoroutineType[t.Any, t.Any, t.Literal[True]]
]
type PredicateT = t.Callable[[dc.Interaction], t.Literal[True]]


def _not_permitted[T: AnyRankT](my_rank: T, rank_required: T) -> FeedbackError:
    return FeedbackError(
        "Not Permitted",
        t"You must at least have the rank `{rank_required}`, but your rank is only `{my_rank}`!",
    )


def rank_required(
    rank_required: AnyRankT, /, *ranks_required: AnyRankT
) -> AsyncPredicateT:
    async def predicate_func(interaction: dc.Interaction) -> t.Literal[True]:
        server_rank: ServerRank | None = None
        jumpedia_rank: JumpediaRank | None = None
        community_rank: CommunityRank | None = None

        jumpedia_and_user: tuple[JumpediaAdapter, JumpediaUserAdapter] | None = None

        def get_jumpedia_and_jumpedia_user() -> (
            tuple[JumpediaAdapter, JumpediaUserAdapter]
        ):
            nonlocal jumpedia_and_user

            if jumpedia_and_user is not None:
                return jumpedia_and_user

            jumpedia = InteractionAdapter(interaction).jumpedia
            jumpedia_user = jumpedia.get_or_create_current_jumpedia_user()

            jumpedia_and_user = (jumpedia, jumpedia_user)

            return jumpedia_and_user

        def get_jumpedia_rank() -> JumpediaRank:
            nonlocal jumpedia_rank

            if jumpedia_rank is not None:
                return jumpedia_rank

            jumpedia_rank = get_jumpedia_and_jumpedia_user()[1].jumpedia_rank

            return jumpedia_rank

        def get_server_rank() -> ServerRank:
            nonlocal server_rank

            if server_rank is not None:
                return server_rank

            server_rank = InteractionAdapter(interaction).current_member.server_rank

            return server_rank

        def get_community_rank() -> CommunityRank:
            nonlocal community_rank

            if community_rank is not None:
                return community_rank

            jumpedia, jumpedia_user = get_jumpedia_and_jumpedia_user()

            community_rank = (
                jumpedia.get_current_community()
                .get_or_create_community_user(jumpedia_user)
                .community_rank
            )

            return community_rank

        for req in (rank_required, *ranks_required):
            # Power == 0 required
            if not req:
                continue

            # Doesn't need database, therefore cheapest, therefore do first
            if isinstance(req, ServerRank):
                sr = get_server_rank()

                if sr >= req:
                    continue

                if get_jumpedia_rank():
                    continue

                raise _not_permitted(sr, req)

            if isinstance(req, JumpediaRank):
                jr = get_jumpedia_rank()

                if jr >= req:
                    continue

                raise _not_permitted(jr, req)

            if isinstance(req, CommunityRank):
                if get_jumpedia_rank():
                    continue

                cr = get_community_rank()

                if cr >= req:
                    continue

                raise _not_permitted(cr, req)

            t.assert_never(req)

        return True

    return predicate_func
