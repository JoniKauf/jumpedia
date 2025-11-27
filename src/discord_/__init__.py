import importlib
import inspect
import os
import pkgutil
import types
import typing as t
from pathlib import Path

import discord as dc
import mariadb
from discord import app_commands as acmds
from discord.ext import commands as cmds

from adapters.errors import EmptyStringFeedbackError
from discord_.utils_ import messaging
from utils import secret, text

from .errors import BaseUserReturnableError

BOT = cmds.Bot(command_prefix="33e32r230ro2dd", intents=dc.Intents.none())
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

    if not interaction.response.is_done():
        await interaction.response.defer()

    if (
        isinstance(e, acmds.errors.TransformerError)
        and e.type is dc.AppCommandOptionType.user
        and isinstance(e.value, dc.User)
    ):
        e = errors.FeedbackError(
            "Non Server Member specified",
            t"The user `{e.value.global_name or e.value.name}` is not a member of this server.",
        )

    if isinstance(e, text.EmptyStringError):
        e = EmptyStringFeedbackError()

    if isinstance(e, BaseUserReturnableError):
        await interaction.followup.send(str(e), **e.msg_kwargs)
        return

    if DEV_MODE:
        await interaction.followup.send(f"Unhandled Exception!\n{error.args}")
        raise e

    if isinstance(e, mariadb.Error):
        await interaction.followup.send(
            messaging.layout(
                "Unhandled Database Error",
                t"An unknown database error occurred. Please try again!",
                messaging.MessageStatus.ERROR,
            )
        )
        return

    await interaction.followup.send(
        messaging.layout(
            "Unhandled Error",
            t"An unhandled error has occurred!",
            messaging.MessageStatus.ERROR,
            additional=t"This is a bug. It will be logged internally and fixed soon.",
        )
    )


TOKEN = secret.listen().DISCORD_TOKEN
BOT.run(TOKEN)
