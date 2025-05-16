import discord as dc
import discord.app_commands as acmds
import discord.ext.commands as cmds

from discordtools import autocompletes, messagetools

from database import queries

class Attr(cmds.GroupCog, group_name="attr"):
    def __init__(self, bot: cmds.Bot) -> None:
        self.bot = bot

    
    
    
async def setup(bot: cmds.Bot):
    await bot.add_cog(Attr(bot))