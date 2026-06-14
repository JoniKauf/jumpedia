import itertools
from string.templatelib import Template
import typing as t

import discord

from domain.entities.base import BaseEntity
from domain.errors import StrStore
from infrastructure import pastee
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
    interaction: discord.Interaction, info_dto_type: type[format.MentionableInfoDTOT], data: t.Mapping[str, tuple[str, ...]]
) -> None:
    links = pastee.table_to_pastee_strings(tuple(data), (itertools.zip_longest(*data.values(), fillvalue=""),))

    await interaction.followup.send(layout.layout(
        t"{format.type_name_title(info_dto_type)} Info", 
        t"{'\n'.join(links) @ T.RAW}", 
        Status.INFO
    ))

async def object_browse(
    interaction: discord.Interaction, summary_dto_type: type[format.MentionableSummaryDTOT], data: t.Mapping[str, tuple[tuple[str, ...], ...]]
) -> None:
    links = pastee.table_to_pastee_strings(tuple(data), data.values())

    await interaction.followup.send(layout.layout(
        t"{format.type_name_title(summary_dto_type)} Browsed",
        t"{'\n'.join(links) @ T.RAW}",
        Status.INFO
    ))

async def object_created(
    interaction: discord.Interaction,
    entity: format.MentionableEntityT,
) -> None:
    await success(
        interaction,
        t"{format.type_name_title(type(entity))} Created",
        t"The {format.mention(entity)} has successfully been created!",
    )


async def object_nuked(interaction: discord.Interaction, dto: format.MentionableDeletedDTOT) -> None:
    await success(
        interaction,
        t"{format.type_name_title(type(dto))} Deleted",
        t"The {format.mention(dto)} has successfully been nuked!",
    )
