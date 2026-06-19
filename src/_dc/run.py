import importlib
import inspect
import os
import pkgutil
import traceback
import types
import typing as t
from pathlib import Path
from traceback import print_exc

import discord as dc
from discord import HTTPException, InteractionResponded
from discord import app_commands as acmds
from discord.ext import commands as cmds

from utils import secret, text

BOT = cmds.Bot(command_prefix="j!", intents=dc.Intents.default())
DEV_MODE: bool = False


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
    from _dc_utils.errors import (
        BaseUserReturnableError,
        DoubleBacktick,
        EmptyString,
        FeedbackError,
        Unhandled,
    )

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

    msg_kwargs: dict[str, t.Any]
    e_old = e

    if isinstance(e, BaseUserReturnableError):
        msg_kwargs = e.msg_kwargs

    else:
        if DEV_MODE:
            await interaction.followup.send(f"Unhandled Exception!\n{e.args}")
            raise e

        e = Unhandled()
        msg_kwargs = {}

        traceback.print_exception(type(e_old), e_old, e_old.__traceback__)

    try:
        await interaction.response.defer()
    except (HTTPException, InteractionResponded):
        pass

    await interaction.followup.send(str(e), **msg_kwargs)


TOKEN = secret.listen().DISCORD_TOKEN
BOT.run(TOKEN)
