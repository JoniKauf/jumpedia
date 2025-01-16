import discord as dc
from discord.ext import commands as cmds
from discord import app_commands as acmds

from discordtools import autocompletes, messagetools
from trickjump import attributes as attrs

from database import queries

class Attr(cmds.GroupCog, group_name="attr"):
    def __init__(self, bot: cmds.Bot) -> None:
        self.bot = bot

    bundle_group = acmds.Group(name="bundle", description="Attr Bundle Group")

    BUNDLE_ATTR_CHOICES = [
        cls.NAME for cls in attrs.ATTR_CLASSES 
        if issubclass(cls, attrs.AttrStrBundle)
    ]
    
    @bundle_group.command()
    @acmds.autocomplete(
        attr=autocompletes.best_match_paged(
            BUNDLE_ATTR_CHOICES, per_page_limit=5
        )
    )
    async def add_item(self, ia: dc.Interaction, attr: str, arguments: str):
        await messagetools.success(ia, "Work In Progress", "Coming soon...")
    
    
async def setup(bot: cmds.Bot):
    await bot.add_cog(Attr(bot))