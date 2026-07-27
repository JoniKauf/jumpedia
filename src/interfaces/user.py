import enum
import typing as t

import discord
from discord import app_commands

from domain.enums.concept import Concept
from domain.enums.rank import CommunityRank, MetaRank
from domain.sentinels.default import DEFAULT
from domain.sentinels.unknown import UNKNOWN
from domain.typing.common import ID
from domain.typing.user import UserID
from domain.value_objects.list import ListNameStr
from domain.value_objects.user import UserNameStr
from interfaces.base import BaseInterface
from interfaces.bindings import user_ref
from interfaces.command import cogs, groups
from interfaces.decorators.with_context import CommandContext, with_context
from interfaces.message import formatting, mentionable, messages
from interfaces.message.formatting import F


class UserInterface(
    BaseInterface, group_name=cogs.cog_concept_to_group_name(Concept.USER, plural=False)
):
    edit_group = groups.create_edit_group()

    MetaRanksEnum = enum.Enum(
        "MetaRanksEnum",
        [(formatting.get_name_of_mentionable(rank), rank.value) for rank in MetaRank]
        + [],
    )

    @edit_group.command(name="meta_rank")
    @with_context()
    async def edit_meta_rank(
        self, ctx: CommandContext, user: discord.User, rank: MetaRanksEnum
    ) -> None:
        new_rank = MetaRank(rank.value)

        del rank

        edited = ctx.services.user.edit_meta_rank(user_ref.user_ref(user), new_rank)

        await messages.success(
            ctx.interaction,
            t"{F.format(Concept.USER)} {F.format(Concept.META_RANK)} Edited",
            t"The {F.full_mention(edited.before)} has been "
            + (t"demoted" if edited.before.meta_rank > new_rank else t"promoted")
            + t" to the {F.full_mention(new_rank)} successfully!",
        )

    CommunityRanksEnum = enum.Enum(
        "CommunityRanksEnum",
        [
            (formatting.get_name_of_mentionable(rank), rank.value)
            for rank in CommunityRank
        ]
        + [],
    )

    @edit_group.command(name="community_rank")
    @with_context()
    async def edit_community_rank(
        self, ctx: CommandContext, user: discord.User, rank: CommunityRanksEnum
    ) -> None:
        new_rank = CommunityRank(rank.value)

        del rank

        edited = ctx.services.member.edit_community_rank(
            user_ref.user_ref(user), new_rank
        )

        await messages.success(
            ctx.interaction,
            t"{F.format(Concept.COMMUNITY_RANK)} Edited",
            t"The {F.full_mention(edited.before)} has been "
            + (t"demoted" if edited.before.community_rank > new_rank else t"promoted")
            + t" to the {F.full_mention(new_rank)} successfully!",
        )

    @app_commands.command()
    @with_context()
    async def info(self, ctx: CommandContext, user: discord.User | None = None) -> None:
        info = ctx.services.member_query.get_user_and_member_info(
            user_ref.user_ref(user),
        )

        # We unpack dicts instead of just adding items conditionally because
        # like this we have the xact order we want
        data: dict[str, tuple[str, ...]] = {
            "ID": (str(info.user.user_id),),
            "Name": (str(info.user.name),),
            **(
                {}
                if info.server_rank is UNKNOWN
                else {
                    "Server Rank": (
                        mentionable.get_name_of_mentionable(info.server_rank),
                    )
                }
            ),
            **(
                {}
                if info.member_info is None
                else {
                    "Community Rank": (
                        mentionable.get_name_of_mentionable(
                            info.member_info.member.community_rank
                        ),
                    ),
                }
            ),
            "Meta Rank": (mentionable.get_name_of_mentionable(info.user.meta_rank),),
            **(
                {}
                if info.member_info is None
                else {
                    "Selected List": (
                        ()
                        if info.member_info.selected_list is None
                        else (
                            mentionable.get_name_of_mentionable(
                                info.member_info.selected_list
                            ),
                        )
                    ),
                }
            ),
        }

        await messages.object_info(
            ctx.interaction,
            info.user if info.member_info is None else info.member_info.member,
            data,
        )

    @edit_group.command(name="selected_list")
    @with_context()
    async def edit_selected_list(
        self,
        ctx: CommandContext,
        list_name: str | None = None,
        user: discord.User | None = None,
    ) -> None:
        edited = ctx.services.member.edit_selected_list(
            None if list_name is None else ListNameStr(list_name),
            user_ref.user_ref(user),
        )

        await messages.success(
            ctx.interaction,
            t"Selected {F.format(Concept.LIST)} Edited",
            t"The selected {F.format(Concept.LIST)} of the {F.full_mention(edited.before)} has been "
            + (
                t"unset"
                if edited.list_after is None
                else t"set as the {F.full_mention(edited.list_after)}"
            )
            + t" successfully!",
        )
