from contextlib import contextmanager
from dataclasses import dataclass
import enum
from functools import wraps
from threading import RLock
from typing import TYPE_CHECKING, Annotated, Any, Callable, Final, Hashable, Iterator, Protocol, Sequence, assert_never, final, overload

import mariadb.cursors

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



class KeyCheck(enum.Enum):
    NONE = enum.auto()
    FIRST = enum.auto()
    ALL = enum.auto()


@dataclass(frozen=True)
class Column:
    name: str
    
    def __str__(self) -> str:
        return f'`{self.name}`'


_ANNOTATIONS = '__annotations'

class BaseRowMeta(type):
    def __new__(cls, name: str, bases: tuple[type, ...], namespace: dict[str, Any]) -> type:
        annotations = namespace.get('__annotations__', {})
        namespace.update({k: Column(k) for k in annotations})
        namespace[_ANNOTATIONS] = frozenset(annotations)

        return super().__new__(cls, name, bases, namespace)
    
    def __str__(self) -> str:
        return f"`{self.__name__}`"
        
class BaseRow(metaclass=BaseRowMeta):
    @classmethod
    def _get_annotations(cls) -> frozenset[str]:
        return getattr(cls, _ANNOTATIONS)
    
    def __init__(self, row: dict[str, Any], key_check: bool = True) -> None:
        if self.__class__ == BaseRow:
            raise RuntimeError

        if key_check and self.__class__._get_annotations() != frozenset(row):
            raise ValueError
        
        self.__dict__ = row


@final
class Rows[T: BaseRow]:
    def __init__(self, rows_data: Sequence[dict[str, Any]], row_type: type[T], key_check: KeyCheck = KeyCheck.FIRST) -> None:
        self.row_type = row_type 

        if not rows_data:
            self.rows = ()
            return
        
        if key_check is not KeyCheck.NONE:
            annotations = row_type._get_annotations()

            if key_check is KeyCheck.FIRST:
                if frozenset(rows_data[0]) != annotations:
                    raise ValueError
                
            elif key_check == KeyCheck.ALL:
                if not all(frozenset(row) == annotations for row in rows_data):
                    raise ValueError
                
            else:
                assert_never(key_check)

        self.rows = tuple(map(lambda row_data: row_type(row_data, False), rows_data))

    def __iter__(self) -> Iterator[T]:
        yield from self.rows


class Cell[TOwner: Any, TValue: Any]:
    def __init__(self, wrapped: Callable[[TOwner], TValue] | Callable[[type[TOwner]], Column]):
        self.__wrapped__ = wrapped
    
    def __set_name__(self, owner: type[TOwner], name: str):
        self.column = Column(name)

    @overload
    def __get__(self, instance: TOwner, owner: type[TOwner]) -> TValue:
        pass
    
    @overload
    def __get__(self, instance: None, owner: type[TOwner]) -> Column:
        pass

    def __get__(self, instance: TOwner | None, owner: type[TOwner]) -> TValue | Column:
        if instance is None:
            return self.column
        
        return self.__wrapped__(instance)

class CellAlias[TOwner: Any, TValue: Any]:
    def __init__(self, wrapped: Callable[[TOwner], TValue] | Callable[[type[TOwner]], Column]):
        self.__wrapped__ = wrapped

    @overload
    def __get__(self, instance: TOwner, owner: type[TOwner]) -> TValue:
        pass
    
    @overload
    def __get__(self, instance: None, owner: type[TOwner]) -> Column:
        pass

    def __get__(self, instance: TOwner | None, owner: type[TOwner]) -> TValue | Column:
        if instance is None:
            return self.__wrapped__(owner)  # type: ignore
        
        return self.__wrapped__(instance)

class Human:
    @Cell
    def name(obj) -> str:
        return 
    
    @CellAlias
    def age(obj) -> int:
        return 
