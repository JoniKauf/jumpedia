import itertools
import typing as t
from string.templatelib import Template

import discord

from domain.entities.base import BaseEntity
from domain.errors import Str
from infrastructure import pastee
from interfaces.message import format, layout
from interfaces.message.layout import Status, T


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
    interaction: discord.Interaction,
    info_dto_type: type[format.MentionableInfoDTOT],
    data: t.Mapping[str, tuple[str, ...]],
) -> None:
    links = pastee.table_to_pastee_strings(
        tuple(data), (itertools.zip_longest(*data.values(), fillvalue=""),)
    )

    await info(
        interaction,
        t"{format.type_name_for_header(info_dto_type)} Info",
        t"{'\n'.join(links) @ T.RAW}",
    )


async def object_browse(
    interaction: discord.Interaction,
    summary_dto_type: type[format.MentionableSummaryDTOT],
    data: t.Mapping[str, tuple[tuple[str, ...], ...]],
) -> None:
    header = t"{format.type_name_for_header(summary_dto_type)} Browsed"

    if not data:
        return await info(
            interaction,
            header,
            t"No {format.type_name_for_body(summary_dto_type)} with the specified criteria could be found!",
        )

    links = pastee.table_to_pastee_strings(tuple(data), data.values())
    count: int = len(
        next(iter(data.values()))
    )  # Count length of first value in the mapping

    await info(
        interaction,
        header,
        t"A total of {count @ T.EMBED} {format.type_name_for_body(summary_dto_type, count == 1)} were found with the specified criteria!\n\n{'\n'.join(links) @ T.RAW}",
    )


async def object_created(
    interaction: discord.Interaction,
    entity: format.MentionableEntityT,
) -> None:
    await success(
        interaction,
        t"{format.type_name_for_header(type(entity))} Created",
        t"The {format.mention_body(entity)} has been created successfully!",
    )


async def object_nuked(
    interaction: discord.Interaction, dto: format.MentionableDeletedDTOT
) -> None:
    await success(
        interaction,
        t"{format.type_name_for_header(type(dto))} Deleted",
        t"The {format.mention_body(dto)} has been nuked successfully! 💣",
    )


async def object_name_edited(
    interaction: discord.Interaction, name_before: Str, entity: format.MentionableEntityT
) -> None:
    await success(
        interaction,
        t"{format.type_name_for_header(type(entity))} Renamed",
        t"The attribute {name_before @ format.T.FORMATTED} has been renamed to {entity.name @ format.T.FORMATTED} successfully!"
    )