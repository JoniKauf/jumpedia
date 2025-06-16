import discord as dc
import discord.app_commands as acmds
import discord.ext.commands as cmds

from discord_structures import predicates
from discordtools import msg, feedbackerrors as fbe

class TaskCog(cmds.GroupCog, group_name="task"):
    def __init__(self, bot: cmds.Bot) -> None:
        self.bot = bot


async def setup(bot: cmds.Bot):
    await bot.add_cog(TaskCog(bot))