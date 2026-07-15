import itertools
import typing as t
from string.templatelib import Template

import discord
from discord import ui
from discord.abc import MISSING

from domain.errors.business import Str
from infrastructure import pastee
from interfaces.message import format, layout, views
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


async def warning(
    interaction: discord.Interaction, header: Template, body: Template
) -> None:
    await interaction.followup.send(layout.layout(header, body, Status.WARNING))


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


async def object_name_edited(
    interaction: discord.Interaction,
    entity_type: type[format.MentionableEntityT],
    before: Str,
    after: Str,
) -> None:
    await success(
        interaction,
        t"{format.type_name_for_header(entity_type)} Renamed",
        t"The {format.type_name_for_body(entity_type)} {before @ format.T.FORMATTED} has been renamed to {after @ format.T.FORMATTED} successfully!",
    )


async def object_aliases_edited(
    interaction: discord.Interaction, entity: format.MentionableEntityT
) -> None:
    await success(
        interaction,
        t"{format.type_name_for_header(type(entity))} Renamed",
        t"The aliases of the {format.mention_body(entity)} have been edited successfully!\n",
    )


async def nuke_object_on_confirmation(
    interaction: discord.Interaction,
    *,
    to_nuke: format.MentionableEntityT,
    parent: format.MentionableEntityT | None,
    consequences: Template,
    execute: t.Callable[[], None],
) -> None:
    TIMEOUT: t.Final[int] = 60

    of_parent_text = t"" if parent is None else t" of the {format.mention_body(parent)}"

    view = views.DangerousConfirmView(
        user=interaction.user,
        on_confirm=execute,
        success_text=layout.layout(
            t"{format.type_name_for_header(type(to_nuke))} Deleted",
            t"The {format.mention_body(to_nuke)}"
            + of_parent_text
            + t" has been deleted (nuked) successfully! 💣",
            Status.SUCCESS,
        ),
        cancel_text=layout.layout(
            t"{format.type_name_for_header(type(to_nuke))} Deletion Aborted",
            t"The deletion (nuking) of the {format.mention_body(to_nuke)} has been aborted!\nNothing changed.",
            Status.WARNING,
        ),
        timeout=TIMEOUT,
    )

    view._message = await interaction.followup.send(
        layout.layout(
            t"Confirm {format.type_name_for_header(type(to_nuke))} Deletion",
            t"Are you sure you want to delete (nuke) the {format.mention_body(to_nuke)}"
            + of_parent_text
            + t"?\n\n"
            + consequences
            + t"\n\n### This action cannot be undone!"
            + t"\n\nThis view will timeout after "
            + Template(str(TIMEOUT))
            + t" seconds!",
            Status.WARNING,
        ),
        view=view,
        wait=True,
    )
