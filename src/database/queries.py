from contextlib import contextmanager
import functools
import json
from typing import TYPE_CHECKING, Any, Callable, ContextManager, Hashable, Iterable, Iterator, Literal, NewType, Optional as Opt
from types import EllipsisType
from structures import jumpedia
from structures.community import Community
import sqlite3
import discord as dc

import mariadb.cursors

from . import mariadb_extensions as mdbe
from database import secret
import mariadb
from discordtools import feedbackerrors as fbe

if TYPE_CHECKING:
    from structures.jumpedia import Jumpedia

@functools.lru_cache(maxsize=1)
def __get_connection_data() -> dict[str, Any]:
    return secret.listen()['DB_CONNECTION_INFO']

@contextmanager
def connected(db: Opt[Community | Jumpedia], auto_commit: bool = True) -> Iterator[tuple[mariadb.Connection, mariadb.cursors.Cursor]]:
    from structures.jumpedia import Jumpedia

    if db is None:
        database = {}
    elif isinstance(db, (Community, Jumpedia)):
        database = {'db': db.database_name}
    else:
        raise TypeError

    conn: Opt[mariadb.Connection] = None
    
    try:
        conn = mariadb.connect(
            **(__get_connection_data() | database),
            converter={
                mariadb.FIELD_TYPE.JSON: lambda json_str: json.loads(json_str)
            }
        )
        cursor = conn.cursor(dictionary=True)

        yield conn, cursor

    except mariadb.Error as e:
        if conn:
            conn.rollback()
        raise e
    
    finally:
        if conn:
            if auto_commit:
                conn.commit()
            cursor.close()
            conn.close()


SYSTEM_DATABASES = {'mysql', 'information_schema', 'performance_schema', 'sys'}

def get_database_names(meta: bool = False, system: bool = False) -> list[str]:
    with connected(None) as (conn, cursor):
        cursor.execute("SHOW DATABASES")
        tmp_result: list[dict[str, str]] = cursor.fetchall()

    result: list[str] = [db['Database'] for db in tmp_result]
    final: list[str] = []

    for db in result:
        if not system and db in SYSTEM_DATABASES:
            continue

        if not meta and db == META_DATABASE_NAME:
            continue

        final.append(db)

    return final


class ParamHelper:
    DEFAULT_PLACEHOLDER: str = "?"

    def __init__(self, placeholder: str = DEFAULT_PLACEHOLDER) -> None:
        self._params: list[Any] = []
        self._placeholder = placeholder

    def __call__(self, param: Any) -> str:
        self._params.append(param)
        return self._placeholder
    
    def __getitem__(self, index: int):
        return self._params[index]
    
    def params(self) -> list[Any]:
        return self._params.copy()
    
    

# def collapse_rows[T: Hashable](
#     rows: list[dict[str, T | Hashable]], 
#     collapse_columns: str, 
#     keep: Callable[[str, Hashable], bool] = lambda col, v: v is not None,
#     collapsed_column_in_data: bool = False
# ) -> dict[T, dict[str, BetterSet[Hashable]]]:
#     result: dict[T, dict[str, BetterSet[Hashable]]] = {}

#     for row in rows:
#         entry = result.setdefault(row[collapse_columns], {})  # type: ignore

#         for col, value in row.items():
#             entry[col] = BetterSet()
            
#             if keep(col, value):
#                 entry[col].add(value)

#             if not collapsed_column_in_data:
#                 entry.pop(collapse_columns)
        
#     return result