import discord as dc
import discord.app_commands as acmds
import discord.ext.commands as cmds

from discordtools import messagetools, predicates
from structures.community import Community
from structures.jumpedia import Jumpedia
from structures.ranks import UserRank

class CommunityCog(cmds.GroupCog, group_name="community"):
    def __init__(self, bot: cmds.Bot) -> None:
        self.bot = bot

    @acmds.command()
    @acmds.check(predicates.permission_user_rank(UserRank.JONIKAUF))
    @acmds.check(predicates.in_guild(None))
    async def create(self, ia: dc.Interaction, name: str) -> None:
        assert ia.guild is not None

        Community.create(Jumpedia(), [ia.guild.id], name)

async def setup(bot: cmds.Bot):
    await bot.add_cog(CommunityCog(bot))