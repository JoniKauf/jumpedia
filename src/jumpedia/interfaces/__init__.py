import logging

from discord.ext import commands

from .attribute import AttributeInterface, AttributesInterface
from .community import CommunitiesInterface, CommunityInterface
from .help import HelpInterface
from .list import ListInterface, ListsInterface
from .server import ServerInterface
from .task import TaskInterface, TasksInterface
from .user import UserInterface

logger = logging.getLogger(__name__)


async def setup(bot: commands.Bot):
    logger.info("Loading interfaces...")

    for cog in [
        AttributeInterface,
        AttributesInterface,
        CommunityInterface,
        CommunitiesInterface,
        HelpInterface,
        ListInterface,
        ListsInterface,
        ServerInterface,
        TaskInterface,
        TasksInterface,
        UserInterface,
    ]:
        logger.info(f"Loading interface {cog.__name__}...")
        await bot.add_cog(cog(bot))

    logger.info("All interfaces loaded!")
