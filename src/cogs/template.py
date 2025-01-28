import discord as dc
import discord.app_commands as acmds
import discord.ext.commands as cmds

from typing import Optional as Opt
from discordtools import messagetools

class Template(cmds.GroupCog, group_name="template"):
    def __init__(self, bot: cmds.Bot) -> None:
        self.bot = bot


async def setup(bot: cmds.Bot):
    await bot.add_cog(Template(bot))