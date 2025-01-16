import discord as dc
from discord.ext import commands as cmds
from discord import app_commands as acmds

from typing import Optional as Opt

from discordtools import messagetools

class List(cmds.GroupCog, group_name="list"):
    def __init__(self, bot: cmds.Bot) -> None:
        self.bot = bot

    trickjump_group = acmds.Group(name="tj", description="List Trickjump Group")

    @trickjump_group.command()
    async def all(self, ia: dc.Interaction, filter: Opt[str], sort: Opt[str]):
        await messagetools.success(ia, "Work In Progress", "Coming soon...")

    @trickjump_group.command()
    async def completed(self, ia: dc.Interaction, user: Opt[int], filter: Opt[str], sort: Opt[str]):
        await messagetools.success(ia, "Work In Progress", "Coming soon...")

    @trickjump_group.command()
    async def missing(self, ia: dc.Interaction, user: Opt[int], filter: Opt[str], sort: Opt[str]):
        await messagetools.success(ia, "Work In Progress", "Coming soon...")


    users_group = acmds.Group(name="users", description="List Users Group")

    @users_group.command()
    async def who_completed(self, ia: dc.Interaction, filter: Opt[str]):
        await messagetools.success(ia, "Work In Progress", "Coming soon...")
    


async def setup(bot: cmds.Bot):
    await bot.add_cog(List(bot))