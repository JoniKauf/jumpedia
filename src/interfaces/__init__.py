from discord.ext import commands

from .attribute import AttributeInterface, AttributesInterface
from .community import CommunitiesInterface, CommunityInterface
from .list import ListInterface, ListsInterface
from .server import ServerInterface
from .task import TaskInterface, TasksInterface
from .user import UserInterface


async def setup(bot: commands.Bot):
    print("Loading interfaces...")

    for cog in [
        AttributeInterface,
        AttributesInterface,
        CommunityInterface,
        CommunitiesInterface,
        ListInterface,
        ListsInterface,
        ServerInterface,
        TaskInterface,
        TasksInterface,
        UserInterface,
    ]:
        print(f"Loading {cog.__name__}...")
        await bot.add_cog(cog(bot))

    print("All interfaces loaded!")
