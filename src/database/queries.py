from contextlib import contextmanager
import functools
import json
import pickle
from threading import RLock
from typing import TYPE_CHECKING, Any, Callable, Final, Hashable, Iterator

import mariadb.connections
import mariadb.cursors

from discordtools import feedbackerrors as fbe
from database import secret
import mariadb

if TYPE_CHECKING:
    from structures.jumpedia import Jumpedia
    from structures.community import Community

# CONVERTER: Final[dict[int, Callable[[Any], Any]]] = {
#     # mariadb.FIELD_TYPE.JSON: lambda json_str: json.loads(json_str),
#     # mariadb.FIELD_TYPE.BLOB: lambda blob: pickle.loads(blob)
# }
__connection_data: dict[str, Any] | None = None

def __get_connection_data() -> dict[str, Hashable]:
    global __connection_data

    if __connection_data is None:
        __connection_data = secret.listen()['DB_CONNECTION_INFO']
    
    return __connection_data


_connections: dict[frozenset[tuple[str, Hashable]], mariadb.Connection] = {}
_lock = RLock()

def _connection_data_to_hashable(connection_data: dict[str, Hashable]) -> frozenset[tuple[str, Hashable]]:
    return frozenset(connection_data.items())

@contextmanager
def connected(commit_on_exit: bool = True, *, no_db: bool = False) -> Iterator[tuple[mariadb.Connection, mariadb.cursors.Cursor]]:
    from structures.jumpedia import Jumpedia
    
    if no_db:
        database = {}
    else:
        database = {'db': Jumpedia().database_name}

    connection_data = __get_connection_data() | database
    hashable = _connection_data_to_hashable(connection_data)

    try:
        with _lock:
            conn = _connections.get(hashable, None)
            
            if conn is None:
                close_conn = True
                _connections[hashable] = conn = mariadb.connect(**connection_data)
            else:
                close_conn = False

        cursor = conn.cursor(dictionary=True)

        yield conn, cursor

    except Exception as e:
        if conn:
            conn.rollback()
        
        raise e
    
    finally:
        if conn is None:
            return
        
        if commit_on_exit:
            conn.commit()
        
        cursor.close()
        
        with _lock:
            if close_conn:
                _connections.pop(hashable)
                conn.close()

            


class ArgHelper:
    """Helper to make inserting parameters into a query easier and more
    intuitive.

    By using the `|` operator after the `ArgHelper` object with an argument (via an f-string) 
    where one would usually put a query placeholder, it will put the placeholder
    in that spot, while being more readable. The parameters can then be
    extracted in that order with the `ArgHelper.params` method.
    """
    DEFAULT_PLACEHOLDER: str = "?"

    def __init__(self, placeholder: str = DEFAULT_PLACEHOLDER) -> None:
        self._params: list[Any] = []
        self._placeholder = placeholder

    def __or__(self, param: Any) -> str:
        self._params.append(param)
        return self._placeholder
    
    def __getitem__(self, index: int):
        return self._params[index]
    
    def steal(self) -> list[Any]:
        tmp = self._params
        self._params = []
        return tmp
    
    def peek(self) -> list[Any]:
        return self._params.copy()
    

def collate_equal(a: str, b: str) -> bool:
    _KEY = "eq"

    with connected() as (_, cursor):
        cursor.execute(f"SELECT ? = ? COLLATE utf8mb4_general_ci AS {_KEY}", (a, b))
    
        return cursor.fetchone()[_KEY]

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