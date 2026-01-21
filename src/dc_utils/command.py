import functools
import typing as t
from types import CoroutineType

import discord as dc
import mariadb
from discord.ext import commands as cmds

from dc_utils import errors

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
