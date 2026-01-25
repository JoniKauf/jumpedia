import functools
import inspect
import itertools
import types
import typing as t
from abc import ABCMeta, abstractmethod
from dataclasses import dataclass
from types import CoroutineType, EllipsisType

import discord as dc
import mariadb
from discord.ext import commands as cmds

import dc_utils
from dc_utils import layouts
from structures import BaseStructure
from utils import gist
from utils.rank import AnyRankT, CommunityRank

if t.TYPE_CHECKING:
    from adapters.interaction import InteractionAdapter


def adapt[T: cmds.Cog, **P](
    rank_to_specify_user: AnyRankT | None | EllipsisType = ...,
) -> t.Callable[
    [
        t.Callable[
            t.Concatenate[T, InteractionAdapter, P],
            CoroutineType[None, None, CoroutineType[t.Any, t.Any, t.Any]],
        ]
    ],
    t.Callable[t.Concatenate[T, dc.Interaction, P], CoroutineType[None, None, None]],
]:
    """Adapt the adapter styled function into a valid command style function of Discord.py.

    Additionally, handle the following:
    - Safely commit or revert all changes made in the command
    - On success, return the success coroutine from the decorated function
    - Handle ``rank_to_specify_user`` if the command has a `user` argument, where the default is `CommunityRank.MODERATOR`
    """

    def adapt_inner(
        func: t.Callable[
            t.Concatenate[T, InteractionAdapter, P],
            CoroutineType[None, None, CoroutineType[t.Any, t.Any, t.Any]],
        ],
    ) -> t.Callable[
        t.Concatenate[T, dc.Interaction, P], CoroutineType[None, None, None]
    ]:
        @functools.wraps(func)
        async def decorated(
            self: T, interaction: dc.Interaction, *args: P.args, **kwargs: P.kwargs
        ) -> None:
            from adapters.interaction import InteractionAdapter
            from dc_utils import errors

            # --- Defer; Always Use Followup ---
            await interaction.response.defer()

            # --- Create Interaction Adapter ---
            ia = InteractionAdapter(interaction)

            # --- Apply Required Rank When 'user' Is Specified ---
            sig = inspect.signature(func)
            bound = sig.bind_partial(self, interaction, *args, **kwargs)
            bound.apply_defaults()

            other_user: dc.User | None | EllipsisType = bound.arguments.get("user", ...)

            nonlocal rank_to_specify_user

            if other_user is ...:  # No user parameter found
                if rank_to_specify_user is not ...:  # No rank must be given then
                    raise KeyError("Could not find parameter 'user'")
            elif (
                rank_to_specify_user is not None
            ):  # If a user parameter is found and a rank is required
                if (
                    rank_to_specify_user is ...
                ):  # Set default rank required if user is found
                    rank_to_specify_user = CommunityRank.MODERATOR

                dc_utils.user.validate_allowed_for_others(
                    interaction, other_user, rank_to_specify_user
                )

            # --- Handle One And Only, Final Commit Per Interaction ---
            try:
                success = await func(self, ia, *args, **kwargs)

                try:
                    if not ia._c._mariadb_connection.autocommit:
                        ia._c.commit()
                except mariadb.Error:
                    raise errors.DatabaseError()

            except Exception:
                ia._c._mariadb_connection.rollback()
                raise

            finally:
                ia._c._mariadb_cursor.close()
                ia._c._mariadb_connection.close()

            # --- Show Success Message ---
            await success

        return decorated

    return adapt_inner


def row_type_to_headers(type: type[t.NamedTuple]) -> tuple[str, ...]:
    return tuple(field.replace("_", " ").title() for field in type._fields)


async def info(ia: InteractionAdapter, structure: BaseStructure, row: t.NamedTuple):
    row_raw: list[tuple[str, ...]] = []

    for v in row:
        if isinstance(v, str):
            row_raw.append((v,))
        else:
            row_raw.append(t.cast(tuple[str, ...], v))

    strings = gist.table_to_gist_strings(
        itertools.zip_longest(*row_raw, fillvalue=""),
        row_type_to_headers(type(row)),
    )

    assert strings

    urls = tuple(
        gist.create_gist(
            {f"Info Data #{str(i).zfill(len(str(len(strings))))}.md": file}
        )
        for i, file in enumerate(strings, 1)
    )

    return ia.dc.followup.send(
        layouts.structure_info(structure, *urls), suppress_embeds=True
    )


async def browse(
    ia: InteractionAdapter,
    structure_type: type[BaseStructure],
    rows: t.Sequence[t.NamedTuple],
    before_send: (
        t.Callable[[list[str]], CoroutineType[t.Any, t.Any, t.Any]] | None
    ) = None,
    edit_msg: dc.WebhookMessage | None = None,
):
    success_func: t.Callable[[str], CoroutineType[t.Any, t.Any, t.Any]] = lambda s: (
        ia.dc.followup.send(s, suppress_embeds=True)
        if edit_msg is None
        else edit_msg.edit(content=s)
    )

    if not rows:
        return success_func(layouts.structure_browsed(structure_type, 0))

    strings = gist.table_to_gist_strings(rows, row_type_to_headers(type(rows[0])))

    assert strings

    # --- Data to gists ---

    if before_send is not None:
        await before_send(strings)

    urls = tuple(
        gist.create_gist(
            {f"Browse Data #{str(i).zfill(len(str(len(strings))))}.md": file}
        )
        for i, file in enumerate(strings, 1)
    )

    assert len(urls) > 0

    return success_func(layouts.structure_browsed(structure_type, len(rows), *urls))
