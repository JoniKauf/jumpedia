from enum import Enum

import discord as dc
import discord.app_commands as acmds
import discord.ext.commands as cmds

from .. import ranks
from ..adapters.interaction import InteractionAdapter
from ..structs import predicates
from ..ranks.community_rank import CommunityRank


class UserCog(cmds.GroupCog, group_name="user"):
    def __init__(self, bot: cmds.Bot) -> None:
        self.bot = bot

    @acmds.command()
    async def rank(self, ia: dc.Interaction, user: dc.User | None = None) -> None:
        ctx = Context(ia)

        if user is None or ia.user.id == user.id:
            server_user = ctx.get_server_user

            rank_info: list[tuple[str, AnyRank]] = [
                ("Server Rank", server_user.server_rank),
                ("Community Rank", server_user.community_rank),
                ("Meta Rank", server_user.meta_rank),
            ]

            return await ia.response.send_message(
                messaging.layout(
                    "Rank Information",
                    "You have the following ranks:\n"
                    + (
                        "\n".join(f"- __{name}:__ `{rank}`" for name, rank in rank_info)
                    ),
                    messaging.MessageStatus.INFO,
                )
            )

        user_id, user_name = helpers.get_user_id_and_name(user)

        community_user = ctx.community.create_or_get_community_user(user_id, user_name)

        rank_info: list[tuple[str, AnyRank]] = [
            ("Community Rank", community_user.community_rank),
            ("Meta Rank", community_user.meta_rank),
        ]

        await ia.response.send_message(
            messaging.layout(
                "Rank Information Retrieved",
                f"The user `{user_name}` has the following ranks:\n"
                + ("\n".join(f"- __{name}:__ `{rank}`" for name, rank in rank_info)),
                messaging.MessageStatus.INFO,
            )
        )

    set_group = acmds.Group(name="set", description="Set data of a user.")

    SetRanks = Enum(
        "PromoteRanks", [(rank.name, rank) for rank in CommunityRank.iter()] + []
    )  # For some reason adding a second list removes type errors

    @set_group.command(
        name="user_community_rank", description="Set a user's community rank."
    )
    @acmds.rename(other_user="user", rank_enum="rank")
    @acmds.check(predicates.rank_required(ranks.get_offset_rank(CommunityRank.USER, 2)))
    async def set_user_community_rank(
        self, interaction: dc.Interaction, other_user: dc.User, rank_enum: SetRanks
    ) -> None:
        ia = InteractionAdapter(interaction)

        other_user_id, other_user_name = (
            ia.jumpedia.get_current_community().get_or_create_community_user()
        )

        other_community_user = ctx.get_community().create_or_get_community_user(
            other_user.id, other_user_name
        )

        new_rank: CommunityRank = rank_enum.value

        if new_rank.power == other_community_user.community_rank.power:
            raise fbe.TemporaryFeedbackError(
                "The new rank for the user is equal to the one they already have."
            )

        community_user = ctx.get_community_user()

        rank_below_mine = ranks.get_offset_rank(community_user.most_important_rank, -1)

        if new_rank.power > rank_below_mine.power:
            raise fbe.TemporaryFeedbackError(
                "The rank you want to give to that user is too high. You must be higher than the rank you want to give."
            )

        ctx.get_community().change_community_user_community_rank(
            other_user_id, other_user_name, new_rank
        )

        what_moted = (
            "promoted"
            if new_rank.power > other_community_user.community_rank.power
            else "demoted"
        )

        await interaction.response.send_message(
            messaging.layout(
                f"User {what_moted.title()}",
                f"The user `{other_user_name}` has successfully been {what_moted} to `{new_rank}`!",
                messaging.MessageStatus.SUCCESS,
            )
        )