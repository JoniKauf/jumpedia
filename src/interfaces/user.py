import enum

import discord

from domain.enums.concept import Concept
from domain.enums.rank import CommunityRank, MetaRank
from domain.typing.common import ID
from domain.typing.user import UserID
from domain.value_objects.user import UserNameStr
from interfaces.base import BaseInterface
from interfaces.command import cogs, groups
from interfaces.decorators.with_context import CommandContext, with_context
from interfaces.message import formatting, messages
from interfaces.message.formatting import F
from services.dtos.user import UserRef


class UserInterface(
    BaseInterface, group_name=cogs.cog_concept_to_group_name(Concept.USER, plural=False)
):
    set_group = groups.create_set_group()

    MetaRanksEnum = enum.Enum(
        "MetaRanksEnum",
        [(formatting.get_name_of_mentionable(rank), rank.value) for rank in MetaRank]
        + [],
    )

    @set_group.command(name="meta_rank")
    @with_context()
    async def set_meta_rank(
        self, ctx: CommandContext, user: discord.User, rank: MetaRanksEnum
    ) -> None:
        new_rank = MetaRank(rank.value)

        del rank

        target_user = ctx.services.user.set_meta_rank(
            UserRef(UserID(ID(user.id)), UserNameStr(user.name)), new_rank
        )

        await messages.success(
            ctx.interaction,
            t"{F.format(Concept.META_RANK)} Set",
            t"The {F.mention(target_user)} has been "
            + (t"demoted" if target_user.meta_rank > new_rank else t"promoted")
            + t" to the {F.mention(new_rank)} successfully!",
        )

    CommunityRanksEnum = enum.Enum(
        "CommunityRanksEnum",
        [
            (formatting.get_name_of_mentionable(rank), rank.value)
            for rank in CommunityRank
        ]
        + [],
    )

    @set_group.command(name="community_rank")
    @with_context()
    async def set_community_rank(
        self, ctx: CommandContext, user: discord.User, rank: CommunityRanksEnum
    ) -> None:
        new_rank = CommunityRank(rank.value)

        del rank

        target_member = ctx.services.member.set_community_rank(
            UserRef(UserID(ID(user.id)), UserNameStr(user.name)), new_rank
        )

        await messages.success(
            ctx.interaction,
            t"{F.format(Concept.COMMUNITY_RANK)} Set",
            t"The {F.mention(target_member)} has been "
            + (t"demoted" if target_member.community_rank > new_rank else t"promoted")
            + t" to the {F.mention(new_rank)} successfully!",
        )
