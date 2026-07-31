import asyncio
import enum
import itertools
import logging
import typing as t
from string.templatelib import Template

import discord

from jumpedia.domain.errors.business import ApiUnreachable
from jumpedia.domain.value_objects.string import Str
from jumpedia.infrastructure import pastee
from jumpedia.interfaces.message import layout, views
from jumpedia.interfaces.message.formattable import FormattableT
from jumpedia.interfaces.message.formatting import F, mentionable_to_formattable
from jumpedia.interfaces.message.layout import Status
from jumpedia.interfaces.message.mentionable import MentionableT

logger = logging.getLogger(__name__)


class SendKwargsT(t.TypedDict):
    ephemeral: t.NotRequired[bool]
    suppress_embeds: t.NotRequired[bool]


async def error(
    interaction: discord.Interaction,
    header: Template,
    body: Template,
    documentation: t.Sequence[str] = (),
    warning: bool = False,
    send_kwargs: SendKwargsT = {},
) -> None:
    header = header + (t"" if warning else t" Error")
    body = Template(*body, "".join(f"\n- {doc}" for doc in documentation))
    status = Status.WARNING if warning else Status.ERROR

    await interaction.followup.send(layout.layout(header, body, status), **send_kwargs)


async def success(
    interaction: discord.Interaction,
    header: Template,
    body: Template,
    send_kwargs: SendKwargsT | None = None,
) -> None:
    await interaction.followup.send(
        layout.layout(header, body, Status.SUCCESS), **(send_kwargs or {})
    )


async def warning(
    interaction: discord.Interaction,
    header: Template,
    body: Template,
    send_kwargs: SendKwargsT | None = None,
) -> None:
    await interaction.followup.send(
        layout.layout(header, body, Status.WARNING), **(send_kwargs or {})
    )


async def info(
    interaction: discord.Interaction,
    header: Template,
    body: Template,
    send_kwargs: SendKwargsT | None = None,
) -> None:
    await interaction.followup.send(
        layout.layout(header, body, Status.INFO), **(send_kwargs or {})
    )


async def object_info(
    interaction: discord.Interaction,
    mentionable: MentionableT,
    data: t.Mapping[str, tuple[str, ...]],
) -> None:
    try:
        links = tuple(
            pastee.create_pastee_with_retries({f"#{i}": s})
            for i, s in enumerate(
                pastee.table_to_pastee_strings(
                    tuple(data),
                    (
                        ((elem,) for elem in row)
                        for row in itertools.zip_longest(*data.values(), fillvalue="")
                    ),
                ),
                start=1,
            )
        )
    except ConnectionError:
        raise ApiUnreachable(Str("pastee"))

    await info(
        interaction,
        t"{F.format(mentionable_to_formattable(mentionable))} Info",
        t"Here is the info for the {F.full_mention(mentionable)}:\n"
        + Template("\n".join(links)),
        {"suppress_embeds": True},
    )


async def object_browse(
    interaction: discord.Interaction,
    formattable: FormattableT,
    data: t.Mapping[str, tuple[tuple[str, ...], ...]],
) -> None:
    header = t"{F.format(formattable, plural=True)} Browsed"

    if all(len(row) == 0 for row in data.values()):
        return await info(
            interaction,
            header,
            t"No {F.format(formattable)} with the specified criteria could be found!",
        )

    try:
        logger.info("Creating pastee tables...")
        paste_strings = pastee.table_to_pastee_strings(
            tuple(data), zip(*data.values(), strict=True)
        )

        logger.info("Creating pastee links...")
        links = await asyncio.gather(
            *(
                asyncio.to_thread(
                    pastee.create_pastee_with_retries,
                    {f"#{i}": s},
                )
                for i, s in enumerate(paste_strings, start=1)
            )
        )
    except ConnectionError:
        raise ApiUnreachable(Str("pastee"))

    count: int = len(
        next(iter(data.values()))
    )  # Count length of first value in the mapping

    plural: bool = count != 1

    logger.info("Sending browse pastees...")
    await info(
        interaction,
        header,
        t"A total of {F.string(str(count), embedded=False)} {F.format(formattable, plural=plural)} {F.raw("were" if plural else "was")} found with the specified criteria!\n\n{F.raw('\n'.join(links))}",
        {"suppress_embeds": True},
    )


async def object_created(
    interaction: discord.Interaction,
    mentionable: MentionableT,
) -> None:
    await success(
        interaction,
        t"{F.format(mentionable_to_formattable(mentionable))} Created",
        t"The {F.full_mention(mentionable)} has been created successfully!",
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
        t"The {F.format(formattable)} {F.string(str(before))} has been renamed to {F.string(str(after))} successfully!",
    )


async def object_aliases_edited(
    interaction: discord.Interaction, mentionable: MentionableT
) -> None:
    await success(
        interaction,
        t"{F.format(mentionable_to_formattable(mentionable))} Renamed",
        t"The aliases of the {F.full_mention(mentionable)} have been edited successfully!\n",
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

    of_parent_text = t"" if parent is None else t" of the {F.full_mention(parent)}"

    view = views.DangerousConfirmView(
        user=interaction.user,
        on_confirm=execute,
        success_text=layout.layout(
            t"{F.format(mentionable_to_formattable(to_nuke))} Deleted",
            t"The {F.full_mention(to_nuke)}"
            + of_parent_text
            + t" has been deleted (nuked) successfully! 💣",
            Status.SUCCESS,
        ),
        cancel_text=layout.layout(
            t"{F.format(mentionable_to_formattable(to_nuke))} Deletion Aborted",
            t"The deletion (nuking) of the {F.full_mention(to_nuke)} has been aborted successfully!\nNothing changed.",
            Status.WARNING,
        ),
        timeout=TIMEOUT,
    )

    view._message = await interaction.followup.send(
        layout.layout(
            t"Confirm {F.format(mentionable_to_formattable(to_nuke))} Deletion",
            t"Are you sure you want to delete (nuke) the {F.full_mention(to_nuke)}"
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

    # If we don't wait, as soon as we send the message for confirmation we leave and
    # ultimately commit. We want to wait until the interaction is finished though!
    await view.wait()
