import logging
from typing import Any

import discord
from discord.ext import commands

import jumpedia.interfaces as interfaces

logger = logging.getLogger(__name__)


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
        await self.tree.sync()
        await self.wait_until_ready()

        logger.info("")
        logger.info("---------- Running ----------")

        if self.user is None:
            logger.critical("Not logged in!")
            exit()

        logger.info(f"Logged in as {self.user} ({self.user.id})")
