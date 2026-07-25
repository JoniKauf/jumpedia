from typing import Any

import discord
from discord.ext import commands

import interfaces


class JumpediaBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()

        super().__init__(
            command_prefix="fbjhkwefhjbwhjfewhjkfweh",
            intents=intents,
        )

    async def setup_hook(self) -> None:
        await self.load_extension(interfaces.__name__)

    async def on_ready(self) -> None:
        print("\n---------- Running ----------")

        if self.user is None:
            print("Not logged in")
            exit()

        print(f"Logged in as {self.user} ({self.user.id})")
