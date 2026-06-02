
from discord import app_commands

from domain.value_objects.community import CommunityName
from interfaces.base import BaseInterface
from interfaces.contexts.command import CommandContext
from interfaces.decorators.context import with_context
from interfaces.message import messages
from interfaces.message.format import Mention


class ServerInterface(BaseInterface, group_name="server"):
    @app_commands.command()
    @with_context()
    async def connect(
        self,
        ctx: CommandContext,
        community: str,
    ) -> None:
        community_entity = ctx.services.community.link(CommunityName(community))
        mention = Mention(community_entity)

        await messages.success(
            ctx.interaction,
            t"Server Connected",
            t"The server was successfully connected to the community {mention.mention}!",
        )

    @app_commands.command()
    @with_context()
    async def disconnect(
        self,
        ctx: CommandContext,
    ) -> None:
        community_entity = ctx.services.community.unlink()
        mention = Mention(community_entity)

        await messages.success(
            ctx.interaction,
            t"Server Disconnected",
            t"The server was successfully disconnected from the community {mention.mention}!",
        )
