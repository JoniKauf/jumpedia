from string.templatelib import Template
import typing as t

import discord

from interfaces.message import layout
from interfaces.message.layout import Status



async def error(
    interaction: discord.Interaction,
    header: Template,
    body: Template,
    documentation: t.Sequence[str] = (),
    warning: bool = False,
    ephemeral: bool = True,
    **kwargs: t.Any
) -> None:
    header = header + t" Error"
    body = Template(*body, ''.join(f"\n- {doc}" for doc in documentation))
    status = Status.WARNING if warning else Status.ERROR

    await interaction.followup.send(layout.layout(header, body, status), ephemeral=ephemeral, **kwargs)