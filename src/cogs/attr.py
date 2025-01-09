import discord as dc
from discord.ext import commands as cmds
from discord import app_commands as acmds

from trickjump import attributes as attrs

class Attr(cmds.GroupCog, group_name="attr"):
    def __init__(self, bot: cmds.Bot) -> None:
        self.bot = bot

    bundle_group = acmds.Group(name="bundle", description="info missing")

    BUNDLE_ATTR_CHOICES = [
        acmds.Choice(name=name, value=name)
        for name, cls
        in attrs.ATTR_ITEMS if issubclass(cls, attrs.AttrStrBundle)
    ]
    
    @bundle_group.command(name="add_item")
    @acmds.choices(attr=BUNDLE_ATTR_CHOICES)
    async def add_item(self, ia: dc.Interaction, attr: str):
        await ia.response.send_message(attr)
    
    
async def setup(bot: cmds.Bot):
    await bot.add_cog(Attr(bot))