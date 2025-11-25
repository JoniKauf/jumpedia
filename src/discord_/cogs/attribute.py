import builtins

import discord as dc
import discord.app_commands as acmds
import discord.ext.commands as cmds

from ..utils_ import messaging


class AttributeCog(cmds.GroupCog, group_name="attribute"):
    def __init__(self, bot: cmds.Bot) -> None:
        self.bot = bot
