import discord as dc
import discord.app_commands as acmds
import discord.ext.commands as cmds

from typing import Optional as Opt
from discordtools import messagetools, predicates
from discordtools.context import Context
from discordtools import feedbackerrors as fbe
from structures.ranks import CommunityRank

class ListCog(cmds.GroupCog, group_name="list"):
    def __init__(self, bot: cmds.Bot) -> None:
        self.bot = bot

    @acmds.command(description="List all lists.")
    async def catalog(self, ia: dc.Interaction) -> None:
        ctx = Context(ia)
        community = ctx.community

        await messagetools.success(
            ia,
            "All Lists",
            ','.join(f"- {list.name}" for list in community.get_lists())
        )
    
        


async def setup(bot: cmds.Bot):
    await bot.add_cog(ListCog(bot))