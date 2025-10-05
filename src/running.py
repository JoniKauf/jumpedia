import os
import traceback
from errors import BaseUserReturnableError

import discord
from discord.ext import commands as cmds
from discord import app_commands as acmds
from database import secret

if __name__ == "__main__":
    raise RuntimeError

SEP = r" \ ".strip()

BOT: cmds.Bot = globals()["BOT"]
TOKEN = secret.listen()["DISCORD_TOKEN"]

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
async def on_app_command_error(
    interaction: discord.Interaction, error: acmds.AppCommandError
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


BOT.run(TOKEN)
