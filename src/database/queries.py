from contextlib import contextmanager
import functools
import json
from typing import Any, Callable, ContextManager, Hashable, Iterable, Iterator, Literal, Optional as Opt
from types import EllipsisType
from utils.custom_collections import BetterSet
import discord as dc

import mariadb.cursors
from . import mariadb_extensions as mdbe
from database import secret
import mariadb
from discordtools import feedbackerrors as fbe

@functools.lru_cache(maxsize=1)
def __get_connection_data() -> dict[str, Any]:
    return secret.listen()['DB_CONNECTION_INFO']

@contextmanager
def connected(community: Literal['master'] | dc.Interaction | str = 'Jumpedia', auto_commit: bool = True) -> Iterator[tuple[mariadb.Connection, mariadb.cursors.Cursor]]:
    conn = None
    extra: dict[str, str] = {}

    if community is None: 
        pass
    elif isinstance(community, str): 
        extra = {'db': community}
    elif isinstance(community, dc.Interaction):
        extra = {'db': 'Jumpedia'}
    else:
        raise TypeError

    try:
        conn = mariadb.connect(
            **(__get_connection_data() | extra),
            converter={
                mariadb.FIELD_TYPE.JSON: lambda json_str: json.loads(json_str)
            }
        )
        cursor = conn.cursor(dictionary=True)

        yield conn, cursor

    except mariadb.Error as e:
        if conn:
            conn.rollback()
        raise fbe.InternalDatabaseError(e)
    finally:
        if conn:
            if auto_commit:
                conn.commit()
            cursor.close()
            conn.close()


def collapse_rows[T: Hashable](
    rows: list[dict[str, T | Hashable]], 
    collapse_columns: str, 
    keep: Callable[[str, Hashable], bool] = lambda col, v: v is not None,
    collapsed_column_in_data: bool = False
) -> dict[T, dict[str, BetterSet[Hashable]]]:
    result: dict[T, dict[str, BetterSet[Hashable]]] = {}

    for row in rows:
        entry = result.setdefault(row[collapse_columns], {})  # type: ignore

        for col, value in row.items():
            entry[col] = BetterSet()
            
            if keep(col, value):
                entry[col].add(value)

            if not collapsed_column_in_data:
                entry.pop(collapse_columns)
        
    return result