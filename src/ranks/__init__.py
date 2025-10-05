import typing as t

from .base_rank import BaseRank
from .community_rank import CommunityRank
from .jumpedia_rank import JumpediaRank
from .server_rank import ServerRank

type AnyRankT = JumpediaRank | CommunityRank | ServerRank


def get_offset_rank(base_rank: AnyRankT, offset: int) -> AnyRankT:
    """
    This hierarchy is kind of confusing:

    Any meta rank (besides NONE) is higher than any other rank.
    Meta ranks therefore basically extend the scale of community ranks
    and server ranks at the top.

    If we need to go down from meta ranks, we use community ranks.
    Server ranks are something that only goes one way.
    """

    if isinstance(base_rank, (JumpediaRank, CommunityRank)):
        scale = CommunityRank.SORTED + JumpediaRank.SORTED[1:]
    else:
        scale = ServerRank.SORTED + JumpediaRank.SORTED[1:]

    idx = scale.index(base_rank) + offset

    if idx < 0:
        return scale[0]

    if idx > len(scale) - 1:
        return scale[-1]

    return scale[idx]


def rank_classes_iter() -> t.Iterator[type[AnyRankT]]:
    return iter(BaseRank.__subclasses__())  # type: ignore
