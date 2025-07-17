from contextlib import contextmanager
from dataclasses import dataclass
import enum
from functools import wraps
from threading import RLock
from typing import TYPE_CHECKING, Annotated, Any, Callable, Final, Hashable, Iterator, Mapping, Never, Protocol, Sequence, assert_never, final, overload

import mariadb.cursors

from database import secret
import mariadb

from database.simple_orm import BaseRow, Rows

if TYPE_CHECKING:
    from structures.jumpedia import Jumpedia
    from structures.community import Community

# CONVERTER: Final[dict[int, Callable[[Any], Any]]] = {
#     # mariadb.FIELD_TYPE.JSON: lambda json_str: json.loads(json_str),
#     # mariadb.FIELD_TYPE.BLOB: lambda blob: pickle.loads(blob)
# }


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


class SimpleOrmCursor:
    def __init__(self, connection: mariadb.Connection, cursor: mariadb.Cursor, arg_helper: ArgHelper | None = None) -> None:
        self._connection = connection
        self._cursor = cursor
        self._arg_helper = arg_helper or ArgHelper()

    def execute(self, statement: Callable[[ArgHelper], str]) -> Any:
        return self._cursor.execute(
            statement(self._arg_helper), 
            self._arg_helper.steal()
        )

    def fetchone[T: BaseRow](self, row_type: type[T]) -> T | None:
        return row_type.get_optional(self._cursor.fetchone())
    
    def fetchmany[T: BaseRow](self, size: int, row_type: type[T]) -> Rows[T]:
        return Rows(self._cursor.fetchmany(size), row_type)
    
    def fetchall[T: BaseRow](self, row_type: type[T]) -> Rows[T]:
        return Rows(self._cursor.fetchall(), row_type)
    
    @property
    def affected_row_count(self) -> int:
        return self._cursor.rowcount
    
    @property
    def last_generated_id(self) -> int:
        id: int | None = self._cursor.lastrowid

        if id is not None:
            return id

        raise LookupError 
        
@contextmanager
def connected(commit_on_exit: bool = True, *, no_db: bool = False) -> Iterator[SimpleOrmCursor]:
    from structures.jumpedia import Jumpedia
    
    if no_db:
        database = {}
    else:
        database = {'db': Jumpedia().database_name}

    connection_data = __get_connection_data() | database
    hashable = _connection_data_to_hashable(connection_data)

    h = ArgHelper()

    try:
        with _lock:
            conn = _connections.get(hashable, None)
            
            if conn is None:
                close_conn = True
                _connections[hashable] = conn = mariadb.connect(**connection_data)
            else:
                close_conn = False

        cursor = conn.cursor(dictionary=True)

        yield SimpleOrmCursor(conn, cursor, h)

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
    

def collate_equal(a: str, b: str) -> bool:
    _KEY = "eq"

    with connected() as (_, cursor):
        cursor.execute(f"SELECT ? = ? COLLATE utf8mb4_general_ci AS {_KEY}", (a, b))
    
        return cursor.fetchone()[_KEY]