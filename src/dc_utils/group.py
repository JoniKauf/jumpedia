from discord import app_commands as acmds

from dc_utils import predicate
from utils.rank import AnyRankT


def create_edit_group(min_required_rank: AnyRankT) -> acmds.Group:
    group = acmds.Group(name="edit", description="Edit...")
    group.interaction_check = predicate.rank_required(min_required_rank)

    return group
