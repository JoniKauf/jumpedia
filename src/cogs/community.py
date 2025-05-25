import discord as dc
import discord.app_commands as acmds
import discord.ext.commands as cmds
from discord import ui
from discordtools import messagetools, predicates, views
from structures.community import Community
from structures.context import Context
from structures.jumpedia import Jumpedia
from structures.ranks import MetaRank, ServerRank, CommunityRank
from discordtools import feedbackerrors as fbe


class CommunityCog(cmds.GroupCog, group_name="community"):
    def __init__(self, bot: cmds.Bot) -> None:
        self.bot = bot
        self.interaction_check = predicates.in_guild(None)

    @acmds.command(description="List all communities.")
    async def catalog(self, ia: dc.Interaction) -> None:
        communities = Jumpedia().get_communities()

        await messagetools.success(
            ia,
            "All Communities",
            '\n'.join(f"- {community.name}" for community in communities),
            show_success=False
        )
        


async def setup(bot: cmds.Bot):
    await bot.add_cog(CommunityCog(bot))