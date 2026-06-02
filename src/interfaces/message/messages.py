from string.templatelib import Template
import typing as t

import discord

from domain.entities.base import BaseEntity
from domain.errors import StrStore
from interfaces.message import format, layout
from interfaces.message.layout import T, Status


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
    interaction: discord.Interaction, header: Template, body: Template
) -> None:
    await interaction.followup.send(layout.layout(header, body, Status.SUCCESS))

async def info(
    interaction: discord.Interaction, header: Template, body: Template
) -> None:
    await interaction.followup.send(layout.layout(header, body, Status.INFO))

async def object_info(
    interaction: discord.Interaction, entity_type: BaseEntity, data: dict[str, tuple[str, ...]]
) -> None:
    await interaction.followup.send(layout.layout(header, body, Status.INFO))

async def object_created(
    interaction: discord.Interaction,
    entity: format.MentionableEntityT,
) -> None:
    mention = format.Mention(entity)

    await success(
        interaction,
        t"{mention.type_title} Created",
        t"The {mention.mention} has successfully been created!",
    )


async def object_nuked(interaction: discord.Interaction, dto: format.MentionableDtoT) -> None:
    mention = format.Mention(dto)

    await success(
        interaction,
        t"{mention.type_title} Deleted",
        t"The {mention.mention} has successfully been nuked!",
    )
