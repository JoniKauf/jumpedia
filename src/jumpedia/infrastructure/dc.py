import logging
import typing as t

import discord
from discord.ext import commands

# Unclean
lazy import jumpedia.interfaces as interfaces

logger = logging.getLogger(__name__)


class _JumpediaBotMeta(type):
    _instances: t.ClassVar[dict[_JumpediaBotMeta, t.Any]] = {}

    def __call__(self, *args, **kwargs):
        if self not in self._instances:
            self._instances[self] = super(_JumpediaBotMeta, self).__call__(
                *args, **kwargs
            )
        return self._instances[self]

    @property
    def instance(self) -> JumpediaBot:
        return self._instances[self]


class JumpediaBot(commands.Bot, metaclass=_JumpediaBotMeta):
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
