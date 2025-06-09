
from typing import Iterator
from structures.ranks.abstract_rank import AbstractRank
from structures.ranks.community_rank import CommunityRank
from structures.ranks.meta_rank import MetaRank
from structures.ranks.server_rank import ServerRank

type AnyRank = MetaRank | CommunityRank | ServerRank

def get_offset_rank(base_rank: AnyRank, offset: int) -> AnyRank:
    """
    This hierarchy is kind of confusing:

    Any meta rank (besides NONE) is higher than any other rank.
    Meta ranks therefore basically extend the scale of community ranks
    and server ranks at the top.

    If we need to go down from meta ranks, we use community ranks.
    Server ranks are something that only goes one way.
    """
    
    if isinstance(base_rank, (MetaRank, CommunityRank)):
        scale = CommunityRank.SORTED + MetaRank.SORTED[1:]
    else:
        scale = ServerRank.SORTED + MetaRank.SORTED[1:]
    
    idx = scale.index(base_rank) + offset

    if idx < 0:
        return scale[0]
    
    if idx > len(scale) - 1:
        return scale[-1]
    
    return scale[idx]


def rank_classes_iter(cls: type['AbstractRank']) -> Iterator['AbstractRank']:
    return iter(cls._lookup.values())