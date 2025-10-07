import importlib
import traceback

import importlib
import pkgutil
import discord as dc
from discord import app_commands as acmds
from discord.ext import commands as cmds

from ..database import secret
from ..errors import BaseUserReturnableError

BOT = cmds.Bot(
    command_prefix="33e32r230ro2dd", intents=dc.Intents.default()
)


def _get_all_cogs_from_package(package: str):
    modules = (
        importlib.import_module(module_name, package)
        for _, module_name, _ in pkgutil.iter_modules([package])
    )

    return (
        obj(BOT) for module in modules
            for obj in module.__dict__.values()
        if issubclass(obj, cmds.Cog)
    )
        
@BOT.event
async def on_ready():
    try:
        for cog in _get_all_cogs_from_package('.cogs'):
            await BOT.add_cog(cog)

        await BOT.tree.sync()
        await BOT.wait_until_ready()
    except BaseException as e:
        traceback.print_exc()
        exit(1)


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