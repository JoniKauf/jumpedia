import enum
import typing as t
from string import Template

import discord
from discord import app_commands

from jumpedia.domain.errors.business import UnknownCommand
from jumpedia.domain.value_objects.string import Str
from jumpedia.infrastructure import dc

lazy from jumpedia.interfaces import PLURAL_TO_SINGULAR
from jumpedia.interfaces.base import BaseInterface
from jumpedia.interfaces.contexts.command import CommandContext
from jumpedia.interfaces.decorators.with_context import with_context
from jumpedia.interfaces.message import messages
from jumpedia.interfaces.message.formatting import F


def get_commands() -> frozenset[str]:
    return frozenset(
        (cmd.qualified_name.lower())
        for cmd in dc.JumpediaBot.instance.tree.walk_commands()
        if not isinstance(cmd, app_commands.Group)
    )


def get_singular_to_plural_command_name() -> frozendict[str, str]:
    return frozendict(
        {
            str(pinter.__cog_group_name__)
            .lower(): str(sinter.__cog_group_name__)
            .lower()
            for pinter, sinter in PLURAL_TO_SINGULAR.items()
        }
    )


async def command_autocomplete(
    interaction: discord.Interaction, current: str
) -> list[app_commands.Choice[str]]:
    COMMANDS = get_commands()

    res: list[str] = []

    current = current.lower()

    for cmd in COMMANDS:
        if current == cmd:
            res.append(cmd)
            break

    for cmd in COMMANDS:
        if cmd.startswith(current):
            res.append(cmd)

    for cmd in COMMANDS:
        if current in cmd:
            res.append(cmd)

    return [
        app_commands.Choice(name=cmd, value=cmd)
        for cmd in tuple(dict.fromkeys(res))[:25]
    ]


class HelpInterface(BaseInterface, group_name="help"):
    @app_commands.command()
    @app_commands.autocomplete(command=command_autocomplete)
    @with_context()
    async def command(self, ctx: CommandContext, command: str) -> None:
        cmd = Str(command.lower())

        del command

        COMMANDS = get_commands()

        if str(cmd) not in COMMANDS:
            raise UnknownCommand(cmd)

        parts = tuple(str(cmd).split())

        assert len(parts) > 0

        page = get_singular_to_plural_command_name().get(parts[0]) or parts[0]

        link = f"https://docs.jumpedia.dev/commands/{page}"

        if len(parts) > 1:
            link += f"#{'-'.join(parts)}"

        await messages.info(
            ctx.interaction,
            t"Help For Command",
            t"Here is the help page for the command {F.string(str(cmd), short=False)}:\n"
            + t"{F.raw(link)}",
            send_kwargs={"suppress_embeds": True},
        )
