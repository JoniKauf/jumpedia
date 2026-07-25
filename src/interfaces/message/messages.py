import itertools
import typing as t
from string.templatelib import Template

import discord

from domain.errors.business import Str
from infrastructure import pastee
from interfaces.message import layout, views
from interfaces.message.formattable import FormattableT
from interfaces.message.formatting import F, mentionable_to_formattable
from interfaces.message.layout import Status
from interfaces.message.mentionable import MentionableT


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
    formattable: FormattableT,
    data: t.Mapping[str, tuple[str, ...]],
) -> None:
    links = pastee.table_to_pastee_strings(
        tuple(data), (itertools.zip_longest(*data.values(), fillvalue=""),)
    )

    await info(
        interaction,
        t"{F.format(formattable)} Info",
        Template("\n".join(links)),
    )


async def object_browse(
    interaction: discord.Interaction,
    formattable: FormattableT,
    data: t.Mapping[str, tuple[tuple[str, ...], ...]],
) -> None:
    header = t"{F.format(formattable)} Browsed"

    if not data:
        return await info(
            interaction,
            header,
            t"No {F.format(formattable)} with the specified criteria could be found!",
        )

    links = pastee.table_to_pastee_strings(tuple(data), data.values())
    count: int = len(
        next(iter(data.values()))
    )  # Count length of first value in the mapping

    plural: bool = count != 1

    await info(
        interaction,
        header,
        t"A total of {F.raw(str(count))} {F.format(formattable, plural=plural)} {F.raw("were" if plural else "was")} found with the specified criteria!\n\n{F.raw('\n'.join(links))}",
    )


async def object_created(
    interaction: discord.Interaction,
    mentionable: MentionableT,
) -> None:
    await success(
        interaction,
        t"{F.format(mentionable_to_formattable(mentionable))} Created",
        t"The {F.mention(mentionable)} has been created successfully!",
    )


async def object_name_edited(
    interaction: discord.Interaction,
    formattable: FormattableT,
    before: Str,
    after: Str,
) -> None:
    await success(
        interaction,
        t"{F.format(formattable)} Renamed",
        t"The {F.format(formattable)} {F.raw(str(before))} has been renamed to {F.raw(str(after))} successfully!",
    )


async def object_aliases_edited(
    interaction: discord.Interaction, mentionable: MentionableT
) -> None:
    await success(
        interaction,
        t"{F.format(mentionable_to_formattable(mentionable))} Renamed",
        t"The aliases of the {F.mention(mentionable)} have been edited successfully!\n",
    )


async def nuke_object_on_confirmation(
    interaction: discord.Interaction,
    *,
    to_nuke: MentionableT,
    parent: MentionableT | None,
    consequences: Template,
    execute: t.Callable[[], None],
) -> None:
    TIMEOUT: t.Final[int] = 60

    of_parent_text = t"" if parent is None else t" of the {F.mention(parent)}"

    view = views.DangerousConfirmView(
        user=interaction.user,
        on_confirm=execute,
        success_text=layout.layout(
            t"{F.format(mentionable_to_formattable(to_nuke))} Deleted",
            t"The {F.mention(to_nuke)}"
            + of_parent_text
            + t" has been deleted (nuked) successfully! 💣",
            Status.SUCCESS,
        ),
        cancel_text=layout.layout(
            t"{F.format(mentionable_to_formattable(to_nuke))} Deletion Aborted",
            t"The deletion (nuking) of the {F.mention(to_nuke)} has been aborted successfully!\nNothing changed.",
            Status.WARNING,
        ),
        timeout=TIMEOUT,
    )

    view._message = await interaction.followup.send(
        layout.layout(
            t"Confirm {F.format(mentionable_to_formattable(to_nuke))} Deletion",
            t"Are you sure you want to delete (nuke) the {F.mention(to_nuke)}"
            + of_parent_text
            + t"?\n\n"
            + consequences
            + t"\n\n### This action cannot be undone!"
            + t"\n\nThis interaction will timeout after {F.raw(str(TIMEOUT))} seconds!",
            Status.WARNING,
        ),
        view=view,
        wait=True,
    )
