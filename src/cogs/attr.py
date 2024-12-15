import discord as dc
from discord.ext import commands
from discord import app_commands

from discordtools import cogtools

class AttrCog(cogtools.BetterCogGroup):
    def __init__(self, bot: commands.Bot, name: str) -> None:
        self.bot = bot
        super().__init__(name)

    @app_commands.command(name="barack")
    async def barack(self, ia: dc.Interaction):
        await ia.response.send_message("We are so barack!")
        await ia.channel.last_message.add_reaction("😎")
    
    @app_commands.command(name="hawk_tuah")
    async def hawk_tuah(self, ia: dc.Interaction):
        await ia.response.send_message("Spit on that thang!")
        await ia.channel.last_message.add_reaction("💦")
    
async def setup(bot: commands.Bot):
    await bot.add_cog(AttrCog(bot, "attr"))