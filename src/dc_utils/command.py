from abc import ABCMeta, abstractmethod
from dataclasses import dataclass
import functools
import types
import typing as t
from types import CoroutineType

import discord as dc
import mariadb
from discord.ext import commands as cmds

from dc_utils import errors, layouts
from structures import BaseStructure
from utils import gist

if t.TYPE_CHECKING:
    from adapting.interaction import InteractionAdapter


def adapt[T: cmds.Cog, **P](
    func: t.Callable[
        t.Concatenate[T, InteractionAdapter, P],
        CoroutineType[None, None, CoroutineType[None, None, t.Any]],
    ],
) -> t.Callable[t.Concatenate[T, dc.Interaction, P], CoroutineType[None, None, None]]:
    @functools.wraps(func)
    async def decorated(
        self: T, interaction: dc.Interaction, *args: P.args, **kwargs: P.kwargs
    ) -> None:
        from adapting.interaction import InteractionAdapter

        ia = InteractionAdapter(interaction)

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

        await success

    return decorated


class BrowseDataRetriever[T: BaseStructure]:
    def __init__(self, **kwargs: t.Callable[[T], str | tuple[str, ...]]) -> types.NoneType:
        self.kwargs = kwargs

async def browse[T: BaseStructure](ia: InteractionAdapter, structure_type: type[T], structures: t.Iterable[T], data_retriever: BrowseDataRetriever[T], before_send: t.Callable[[list[str]], CoroutineType[t.Any, t.Any, t.Any]] | None = None, edit_msg: dc.WebhookMessage | None = None):
    rows = tuple(
        tuple(retriever(structure) for retriever in data_retriever.kwargs.values()) for structure in structures
    )

    success_func: t.Callable[[str], CoroutineType[t.Any, t.Any, t.Any]] = lambda s: ia.dc.followup.send(s, suppress_embeds=True) if edit_msg is None else edit_msg.edit(content=s)

    if not rows:
        return success_func(layouts.browse(
            structure_type,
            0,
            ()
        ))

    strings = gist.table_to_gist_strings(rows, tuple(data_retriever.kwargs))

    assert strings

    zfill = len(str(len(strings)))

    # --- Data to gists ---

    if before_send is not None:
        await before_send(strings)

    urls = tuple(
        gist.create_gist({f"Data #{str(i).zfill(zfill)}.md": file})
        for i, file in enumerate(strings, 1)
    )

    assert len(urls) > 0

    return success_func(layouts.browse(structure_type, len(rows), urls))