from contextlib import contextmanager
from threading import RLock
from typing import Any, Callable, Final, Hashable, Iterator, Mapping, Never, Protocol, Sequence, assert_never, final, overload
from database import secret
import mariadb

from database.simple_orm import Arg, BaseModel, Rows, column

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


class CursorWrapper:
    def __init__(self, cursor: mariadb.Cursor) -> None:
        self._cursor = cursor

    def execute(self, statement: Callable[[Arg], str]) -> Any:
        arg = Arg()
        return self._cursor.execute(statement(arg), arg.steal())
    
    def fetchone[T: BaseModel](self, model: type[T]) -> T | None:
        return model.opt(self._cursor.fetchone())
    
    def fetchmany[T: BaseModel](self, size: int, model: type[T]) -> Rows[T]:
        return Rows(self._cursor.fetchmany(size), model)
    
    def fetchall[T: BaseModel](self, model: type[T]) -> Rows[T]:
        return Rows(self._cursor.fetchall(), model)
    
    @property
    def affected_row_count(self) -> int:
        return self._cursor.rowcount
    
    @property
    def last_generated_id(self) -> int:
        id: int | Any = self._cursor.lastrowid

        if isinstance(id, int):
            return id

        raise LookupError 
    
    @property
    def connection(self) -> mariadb.Connection:
        return self._cursor.connection

        
@contextmanager
def connected(commit_on_exit: bool = True, *, no_db: bool = False) -> Iterator[CursorWrapper]:
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

        yield CursorWrapper(cursor)

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
    


class _Equal(BaseModel, table_name=None):
    @column(bool)
    def eq(self): pass

def collate_equal(a: str, b: str) -> bool:
    with connected() as c:
        c.execute(lambda arg: f"SELECT {arg(a)} = {arg(b)} COLLATE utf8mb4_general_ci AS {_Equal.eq}")
    
        result = c.fetchone(_Equal)

    return result is not None and result.eq
