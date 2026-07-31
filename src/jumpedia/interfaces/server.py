import discord
from discord import app_commands
from discord.ext import commands

from jumpedia.domain.enums.concept import Concept
from jumpedia.domain.value_objects.community import CommunityNameStr
from jumpedia.interfaces.base import BaseInterface
from jumpedia.interfaces.command import cogs
from jumpedia.interfaces.contexts.command import CommandContext
from jumpedia.interfaces.decorators.with_context import with_context
from jumpedia.interfaces.message import messages
from jumpedia.interfaces.message.formatting import F


class ServerInterface(
    BaseInterface,
    group_name=cogs.cog_concept_to_group_name(Concept.SERVER, plural=False),
):
    @app_commands.command()
    @with_context()
    async def link(
        self,
        ctx: CommandContext,
        community_name: str,
    ) -> None:
        community_entity = ctx.services.server.link(CommunityNameStr(community_name))

        await messages.success(
            ctx.interaction,
            t"Server Connected",
            t"The {F.format(Concept.SERVER)} was successfully linked to the {F.full_mention(community_entity)}!",
        )

    @app_commands.command()
    @with_context()
    async def unlink(
        self,
        ctx: CommandContext,
    ) -> None:
        community_entity = ctx.services.server.unlink()

        await messages.success(
            ctx.interaction,
            t"Server Disconnected",
            t"The {F.format(Concept.SERVER)} was successfully unlinked from the {F.full_mention(community_entity)}!",
        )
