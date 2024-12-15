import inspect
import os
import traceback
from typing import Any, Callable

import discord
from discord import Interaction, app_commands
from discord.ext import commands
from discord.ext.commands import CommandError, Context

from discordtools import errors, messagetools

if __name__ == '__main__':
    raise RuntimeError

TOKEN = JsonDatabases.secret_db.load()['DISCORD_TOKEN']
COMMANDS_PACKAGE = 'cogs'

@bot.event
async def on_ready():
    try:
        for file_name in os.listdir(COMMANDS_PACKAGE):
            file_name = file_name.removesuffix('.py')

            if not file_name.startswith('__'):
                await bot.load_extension(f"{COMMANDS_PACKAGE}.{file_name}")
    except BaseException as e:
        traceback.print_exc()
        exit(1)

    await bot.tree.sync()
    await bot.wait_until_ready()


@bot.tree.error
async def on_app_command_error(interaction: Interaction, error: app_commands.AppCommandError) -> None:
    if isinstance(error, app_commands.CommandInvokeError):
        e = error.original
    elif isinstance(error, app_commands.CheckFailure):
        e = error.args[0]
    else:
        e = error
    
    is_deferred = interaction.response.is_done()

    if isinstance(e, errors.UserReturnableError):
        e.msg_kwargs['content'] = str(e)
        await messagetools.handle_interaction_func(interaction, e.msg_kwargs)
        return

    if not is_deferred:
        await interaction.response.defer()
    
    await interaction.followup.send("Unhandled Exception!")
    raise e


bot.run(TOKEN)