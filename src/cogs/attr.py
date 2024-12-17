import discord as dc
from discord.ext import commands
from discord import app_commands

class ListCog(commands.GroupCog, group_name="list"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    test1 = app_commands.Group(name="test1", description="hihi")
    @test2.command(name="testcmd", description="test")
    async def test(self, ia: dc.Interaction, test: str):
        await ia.response.send_message("aaaa")
    
    
async def setup(bot: commands.Bot):
    await bot.add_cog(ListCog(bot))