import discord as dc
import discord.app_commands as acmds
import discord.ext.commands as cmds

from ..utils_ import predicate


class Template(cmds.GroupCog, group_name="template"):
    def __init__(self, bot: cmds.Bot) -> None:
        self.bot = bot
