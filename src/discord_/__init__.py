import importlib
import inspect
import os
import pkgutil
import traceback
import types
import typing as t

import discord as dc
from discord import app_commands as acmds
from discord.ext import commands as cmds

from ..database import secret
from .errors import BaseUserReturnableError

BOT = cmds.Bot(command_prefix="33e32r230ro2dd", intents=dc.Intents.none())


def _get_all_modules_from_package(pkg_path: str) -> t.Generator[types.ModuleType]:
    rel = (
        os.path.relpath(pkg_path, start=os.getcwd())
        .strip(os.path.sep)
        .replace(os.path.sep, ".")
    )

    # Use pkgutil to iterate over modules in the package
    for importer, modname, ispkg in pkgutil.iter_modules([pkg_path]):
        if ispkg:
            continue

        if modname == "__init__":
            continue

        yield importlib.import_module(f"{rel}.{modname}")


@BOT.event
async def on_ready():
    from . import cogs

    # The one without sin among you should be the first to throw a stone at her.
    for module in _get_all_modules_from_package(os.path.dirname(cogs.__file__)):
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

    if isinstance(e, BaseUserReturnableError):
        e.msg_kwargs["content"] = str(e)
        return await interaction.followup.send(**e.msg_kwargs)

    await interaction.followup.send(f"Unhandled Exception!\n{error.args}")
    raise e


TOKEN = secret.listen().DISCORD_TOKEN
BOT.run(TOKEN)
