from string.templatelib import Template
import typing as t

import discord

from domain.entities.base import BaseEntity
from domain.errors import StrStore
from interfaces.message import format, layout
from interfaces.message.layout import Status


async def error(
    interaction: discord.Interaction,
    header: Template,
    body: Template,
    documentation: t.Sequence[str] = (),
    warning: bool = False,
    ephemeral: bool = True,
    **kwargs: t.Any,
) -> None:
    header = header + t" Error"
    body = Template(*body, "".join(f"\n- {doc}" for doc in documentation))
    status = Status.WARNING if warning else Status.ERROR

    await interaction.followup.send(
        layout.layout(header, body, status), ephemeral=ephemeral, **kwargs
    )


async def success(
    interaction: discord.Interaction,
    header: Template,
    body: Template
) -> None:
    await interaction.followup.send(
        layout.layout(header, body, Status.SUCCESS)
    )

async def created(
    interaction: discord.Interaction,
    entity: format.Mentionable,
) -> None:
    await success(
        interaction,
        t"{format.get_mentionable_type_name(entity).title()} Created",
        t"The {format.mention(entity)} has successfully been created!",
    )

async def nuked(
    interaction: discord.Interaction,
    entity: format.Mentionable
) -> None:
    await success(
        interaction,
        t"{format.get_mentionable_type_name(entity).title()} Deleted",
        t"The {format.mention(entity)} has successfully been nuked!"
    )