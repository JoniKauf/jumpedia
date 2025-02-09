import discord as dc
import discord.app_commands as acmds
import discord.ext.commands as cmds

from typing import Optional as Opt
from discordtools import messagetools
from trickjump import trickjump as tj
import shlex

class Change(cmds.GroupCog, group_name="change"):
    def __init__(self, bot: cmds.Bot) -> None:
        self.bot = bot

    @acmds.command()
    async def add(self, ia: dc.Interaction, data: ):
        parts = data.split("\n")

        current_attr: Opt[str] = None

        for part in parts:
            part = part.strip()

            if not part:
                continue

            part.partition('=')


async def setup(bot: cmds.Bot):
    await bot.add_cog(Change(bot))