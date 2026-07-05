import enum

import discord
from discord import app_commands

from domain.enums.rank import CommunityRank, MetaRank
from domain.types.common import ID
from domain.types.user import UserID
from domain.value_objects.user import UserNameStr
from interfaces.base import BaseInterface
from interfaces.decorators.context import CommandContext, with_context
from interfaces.message import format, messages
from services.dtos.user import UserRef


class UserInterface(BaseInterface, group_name="user"):

    MetaRanksEnum = enum.Enum(
        "MetaRanksEnum",
        [
            (format.get_type_name_lower(rank, singular=True).title(), rank)
            for rank in MetaRank
        ]
        + [],
    )

    @app_commands.command()
    @with_context()
    async def set_meta_rank(
        self, ctx: CommandContext, user: discord.User, rank: MetaRanksEnum
    ) -> None:
        target_user = ctx.services.user.set_meta_rank(
            UserRef(UserID(ID(user.id)), UserNameStr(user.name)), rank.value
        )

        await messages.success(
            ctx.interaction,
            t"Meta Rank Set",
            t"The meta rank of the {format.mention_body(target_user)} has been set to {format.get_instance_name(rank.value) @ format.T.FORMATTED} successfully!",
        )

    CommunityRanksEnum = enum.Enum(
        "CommunityRanksEnum",
        [
            (format.get_type_name_lower(rank, singular=True).title(), rank)
            for rank in CommunityRank
        ]
        + [],
    )

    @app_commands.command()
    @with_context()
    async def set_community_rank(
        self, ctx: CommandContext, user: discord.User, rank: CommunityRanksEnum
    ) -> None:
        target_member = ctx.services.member.set_community_rank(
            UserRef(UserID(ID(user.id)), UserNameStr(user.name)), rank.value
        )

        await messages.success(
            ctx.interaction,
            t"Meta Rank Set",
            t"The meta rank of the {format.mention_body(target_member)} has been set to {format.get_instance_name(rank.value) @ format.T.FORMATTED} successfully!",
        )
