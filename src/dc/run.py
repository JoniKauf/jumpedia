import importlib
import inspect
import os
import pkgutil
import types
import typing as t
from pathlib import Path

import discord as dc
from discord import app_commands as acmds
from discord.ext import commands as cmds

from dc_utils import message
from dc_utils.errors import (
    BaseUserReturnableError,
    DoubleBacktick,
    EmptyString,
    FeedbackError,
)
from utils import secret, text

BOT = cmds.Bot(command_prefix="awjkefejjefejffsn", intents=dc.Intents.default())
DEV_MODE: bool = True


def _get_all_modules_of_cogs(pkg_path: str) -> t.Generator[types.ModuleType]:
    rel = (
        os.path.relpath(pkg_path, start=Path(__file__).resolve().parent.parent)
        .strip(os.path.sep)
        .replace(os.path.sep, ".")
    )

    # Use pkgutil to iterate over modules in the package
    for _, modname, ispkg in pkgutil.iter_modules([pkg_path]):
        if ispkg:
            continue

        if modname.startswith("_"):
            continue

        yield importlib.import_module(f"{rel}.{modname}")


@BOT.event
async def on_ready():
    from . import cogs

    # The one without sin among you should be the first to throw a stone at her.
    for module in _get_all_modules_of_cogs(os.path.dirname(cogs.__file__)):
        for obj in module.__dict__.values():
            if inspect.isclass(obj) and issubclass(obj, cmds.Cog):
                await BOT.add_cog(obj(BOT))

    await BOT.tree.sync()
    await BOT.wait_until_ready()


@BOT.tree.error
async def on_app_command_error(
    interaction: dc.Interaction, error: acmds.AppCommandError
) -> None:
    if isinstance(error, acmds.CommandInvokeError):
        e = error.original
    else:
        e = error

    # Should be deferred already
    # try:
    #     await interaction.response.defer()
    # except (dc.errors.InteractionResponded, dc.HTTPException):
    #     pass

    if (
        isinstance(e, acmds.errors.TransformerError)
        and e.type is dc.AppCommandOptionType.user
        and isinstance(e.value, dc.User)
    ):
        e = FeedbackError(
            "Non Server Member specified",
            t"The user {e.value.global_name or e.value.name:,} is not a member of this server.",
        )

    if isinstance(e, text.EmptyStringError):
        e = EmptyString()
    elif isinstance(e, text.DoubleBacktickError):
        e = DoubleBacktick()

    if isinstance(e, BaseUserReturnableError):
        await interaction.followup.send(str(e), **e.msg_kwargs)
        return

    if DEV_MODE:
        await interaction.followup.send(f"Unhandled Exception!\n{e.args}")
        raise e

    await interaction.followup.send(
        message.layout(
            "Unhandled Error",
            t"An unhandled error has occurred!",
            message.MessageStatus.ERROR,
            additional=t"This is a bug. It will be logged internally and fixed soon.",
        )
    )


from adapting import interaction

interaction._get_or_create_the_one_piece()

TOKEN = secret.listen().DISCORD_TOKEN
BOT.run(TOKEN)
