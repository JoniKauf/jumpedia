import discord as dc
import discord.app_commands as acmds
import discord.ext.commands as cmds

from discordtools import messagetools, predicates, feedbackerrors as fbe

class Template(cmds.GroupCog, group_name="template"):
    def __init__(self, bot: cmds.Bot) -> None:
        self.bot = bot


async def setup(bot: cmds.Bot):
    await bot.add_cog(Template(bot))