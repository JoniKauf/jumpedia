import typing as t
from types import CoroutineType

import discord as dc
from discord import app_commands as acmds

from discord_.utils_ import predicate
from structures import BaseStructure
from structures.jumpedia import Jumpedia
from utils.rank import AnyRankT, CommunityRank


def _mention(structure_type: type[BaseStructure], /) -> str:
    if structure_type is Jumpedia:
        return structure_type.type_name

    return f"a {structure_type.type_name}"


def get_get_group(structure_type: type[BaseStructure], /) -> acmds.Group:
    return acmds.Group(
        name="get",
        description=f"Get a list of all objects that belong to {_mention(structure_type)}.",
    )


def get_create_group(
    structure_type: type[BaseStructure],
    /,
    *ranks_required: AnyRankT,
) -> acmds.Group:
    group = acmds.Group(
        name="create",
        description=f"Create objects that belong to {_mention(structure_type)}.",
    )

    if ranks_required:
        group.interaction_check = predicate.rank_required(*ranks_required)

    return group


def get_delete_group(
    structure_type: type[BaseStructure],
    /,
    *ranks_required: AnyRankT,
) -> acmds.Group:
    group = acmds.Group(
        name="delete",
        description=f"Delete objects that belong to {_mention(structure_type)}.",
    )

    if ranks_required:
        group.interaction_check = predicate.rank_required(*ranks_required)

    return group


def get_set_group(
    structure_type: type[BaseStructure],
    /,
    *ranks_required: AnyRankT,
) -> acmds.Group:
    group = acmds.Group(
        name="set",
        description=f"Set objects that belong to a {_mention(structure_type)}.",
    )

    if ranks_required:
        group.interaction_check = predicate.rank_required(*ranks_required)

    return group
