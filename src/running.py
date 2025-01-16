import inspect
import os
import traceback
from typing import Any, Callable

from discord import app_commands
from discord.ext import commands
from discord.ext.commands import CommandError, Context

import discord
from discordtools import errors, messagetools
from database import secret

if __name__ == '__main__':
    raise RuntimeError

SEP = r" \ ".strip()

BOT: commands.Bot = globals()["BOT"]
TOKEN = secret.listen()['DISCORD_TOKEN']

COGS_DIR = r"cogs"


def get_cogs() -> list[str]:
    return [
        f"{COGS_DIR}.{os.path.splitext(module)[0]}"
        for module in os.listdir(COGS_DIR)
        if not module.startswith("__")
    ]
    
@BOT.event
async def on_ready():
    try:
        for module in get_cogs():
            await BOT.load_extension(module)

        await BOT.tree.sync()
        await BOT.wait_until_ready()
    except BaseException as e:
        traceback.print_exc()
        exit(1)


@BOT.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
    if isinstance(error, app_commands.CommandInvokeError):
        e = error.original
    elif isinstance(error, app_commands.CheckFailure):
        e = error.args[0]
    else:
        e = error
    
    is_deferred = interaction.response.is_done()

    if isinstance(e, errors.UserReturnableError):
        e.msg_kwargs['content'] = str(e)
        await messagetools._handle_interaction_func(interaction, e.msg_kwargs)
        return

    if not is_deferred:
        await interaction.response.defer()
    
    await interaction.followup.send("Unhandled Exception!")
    raise e

BOT.run(TOKEN)