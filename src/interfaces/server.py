from discord import app_commands

from domain.value_objects.community import CommunityNameStr
from interfaces.base import BaseInterface
from interfaces.contexts.command import CommandContext
from interfaces.decorators.context import with_context
from interfaces.message import format, messages


class ServerInterface(BaseInterface, group_name="server"):
    @app_commands.command()
    @with_context()
    async def connect(
        self,
        ctx: CommandContext,
        community_name: str,
    ) -> None:
        community_entity = ctx.services.server.link(CommunityNameStr(community_name))

        await messages.success(
            ctx.interaction,
            t"Server Connected",
            t"The server was successfully connected to the community {format.mention_body(community_entity)}!",
        )

    @app_commands.command()
    @with_context()
    async def disconnect(
        self,
        ctx: CommandContext,
    ) -> None:
        community_entity = ctx.services.server.unlink()

        await messages.success(
            ctx.interaction,
            t"Server Disconnected",
            t"The server was successfully disconnected from the community {format.mention_body(community_entity)}!",
        )
