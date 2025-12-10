import discord.ext.commands as cmds


class AttributeCog(cmds.GroupCog, group_name="attribute"):
    def __init__(self, bot: cmds.Bot) -> None:
        self.bot = bot
