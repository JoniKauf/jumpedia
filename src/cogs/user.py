import discord as dc
import discord.app_commands as acmds
import discord.ext.commands as cmds

from discordtools import helpers, messagetools, predicates, feedbackerrors as fbe
from discordtools.context import Context
from structures.ranks import AnyRank

class UserCog(cmds.GroupCog, group_name="user"):
    def __init__(self, bot: cmds.Bot) -> None:
        self.bot = bot

    @acmds.command()
    async def rank(self, ia: dc.Interaction, user: dc.User | None = None) -> None:
        ctx = Context(ia)

        if user is None or ia.user.id == user.id:
            server_user = ctx.server_user

            rank_info: list[tuple[str, AnyRank]] = [
                ("Server Rank", server_user.server_rank),
                ("Community Rank", server_user.community_rank),
                ("Meta Rank", server_user.meta_rank)
            ]

            return await messagetools.success(
                ia,
                "Rank Information Retrieved",
                "You have the following ranks:\n" +
                ('\n'.join(f"- __{name}:__ `{rank}`" for name, rank in rank_info))
            )

        user_id, user_name = helpers.get_user_id_and_name(user)

        community_user = ctx.community.create_or_get_community_user(
            user_id, user_name
        )

        rank_info: list[tuple[str, AnyRank]] = [
            ("Community Rank", community_user.community_rank),
            ("Meta Rank", community_user.meta_rank)
        ]

        await messagetools.success(
            ia,
            "Rank Information Retrieved",
            f"The user `{user_name}` has the following ranks:\n" +
            ('\n'.join(f"- __{name}:__ `{rank}`" for name, rank in rank_info))
        )
        

async def setup(bot: cmds.Bot):
    await bot.add_cog(UserCog(bot))