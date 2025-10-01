from contextlib import contextmanager
from threading import RLock
from typing import (
    Any,
    Callable,
    Final,
    Hashable,
    Iterator,
    Mapping,
    Never,
    Protocol,
    Sequence,
    Union,
    assert_never,
    final,
    get_args,
    overload,
)
from database import secret, typed
import mariadb
from string.templatelib import Interpolation, Template
from database.simple_orm import (
    Arg,
    BaseModel,
    BaseModelMeta,
    Column,
    Args,
    Raw,
    Rows,
    column,
)
from utils import text

# CONVERTER: Final[dict[int, Callable[[Any], Any]]] = {
#     # mariadb.FIELD_TYPE.JSON: lambda json_str: json.loads(json_str),
#     # mariadb.FIELD_TYPE.BLOB: lambda blob: pickle.loads(blob)
# }


__connection_data: dict[str, Any] | None = None


def __get_connection_data() -> dict[str, Hashable]:
    global __connection_data

    if __connection_data is None:
        __connection_data = secret.listen()["DB_CONNECTION_INFO"]

    return __connection_data


_connections: dict[frozenset[tuple[str, Hashable]], mariadb.Connection] = {}
_lock = RLock()


def _connection_data_to_hashable(
    connection_data: dict[str, Hashable],
) -> frozenset[tuple[str, Hashable]]:
    return frozenset(connection_data.items())


type InterpolationExecuteT = Interpolation[
    Arg.ArgPlaceholder | Raw | BaseModelMeta | Column
]
INTERPOLATION_EXECUTE = get_args(InterpolationExecuteT.__value__)[0]

type InterpolationExecuteManyT = Interpolation[
    Args.ArgsPlaceholder | Raw | BaseModelMeta | Column
]
INTERPOLATION_EXECUTE_MANY = get_args(InterpolationExecuteManyT.__value__)[0]


class CursorWrapper:
    def __init__(self, cursor: mariadb.Cursor) -> None:
        self._cursor = cursor

    def execute(
        self,
        statement: Callable[[Arg], Template[*tuple[InterpolationExecuteT, ...]]],
        /,
    ) -> None:
        arg = Arg()
        template = statement(arg)

        for v in template.values:
            if not isinstance(v, INTERPOLATION_EXECUTE):
                raise TypeError(f"{v!r} not isinstance {INTERPOLATION_EXECUTE!r}")

        self._cursor.execute(text.t_to_f_string(template), arg.steal())

    def executemany(
        self,
        statement: Callable[[Args], Template[*tuple[InterpolationExecuteManyT, ...]]],
        /,
    ) -> None:
        args = Args()
        template = statement(args)

        for v in template.values:
            if not isinstance(v, INTERPOLATION_EXECUTE_MANY):
                raise TypeError()

        self._cursor.executemany(text.t_to_f_string(template), args.steal())

    def fetchone[T: BaseModel](self, model: type[T]) -> T | None:
        row: dict[str, Any] | None = self._cursor.fetchone()

        if row is None:
            return None

        return model(row)

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

    def execute_raw(self, statement: str, /) -> None:
        self._cursor.execute(statement)


@contextmanager
def connected(
    commit_on_exit: bool = True, *, no_db: bool = False
) -> Iterator[CursorWrapper]:
    if no_db:
        database = {}
    else:
        database = {"db": typed.DATABASE_NAME}

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
        if conn is not None:
            if commit_on_exit:
                conn.commit()

            cursor.close()

            with _lock:
                if close_conn:
                    _connections.pop(hashable)
                    conn.close()
