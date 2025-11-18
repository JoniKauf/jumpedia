import typing as t
from types import CoroutineType

import discord as dc
from discord import app_commands as acmds

from discord_.utils_ import predicates
from structures import BaseStructure
from structures.jumpedia import Jumpedia
from structures.user.rank import AnyRankT, CommunityRank


def _mention(structure_type: type[BaseStructure], /) -> str:
    if structure_type is Jumpedia:
        return structure_type.type_name

    return f"a {structure_type.type_name}"


def _get_ranks_interaction_check(
    rank_required: AnyRankT, /, *ranks_required: AnyRankT
) -> t.Callable[[dc.Interaction], CoroutineType[t.Any, t.Any, t.Literal[True]]]:
    async def interaction_check(interaction: dc.Interaction) -> t.Literal[True]:
        for rank in (rank_required, *ranks_required):
            await predicates.rank_required(rank)(interaction)

        return True

    return interaction_check


def get_get_group(structure_type: type[BaseStructure], /) -> acmds.Group:
    return acmds.Group(
        name="get",
        description=f"Get a list of all objects that belong to {_mention(structure_type)}.",
    )


def get_create_group(
    structure_type: type[BaseStructure],
    rank_required: AnyRankT = CommunityRank.HIGHEST,
    /,
    *ranks_required: AnyRankT,
) -> acmds.Group:
    group = acmds.Group(
        name="create",
        description=f"Create objects that belong to {_mention(structure_type)}.",
    )

    group.interaction_check = _get_ranks_interaction_check(
        rank_required, *ranks_required
    )

    return group


def get_delete_group(
    structure_type: type[BaseStructure],
    rank_required: AnyRankT = CommunityRank.HIGHEST,
    /,
    *ranks_required: AnyRankT,
) -> acmds.Group:
    group = acmds.Group(
        name="delete",
        description=f"Delete objects that belong to {_mention(structure_type)}.",
    )

    group.interaction_check = _get_ranks_interaction_check(
        rank_required, *ranks_required
    )

    return group
