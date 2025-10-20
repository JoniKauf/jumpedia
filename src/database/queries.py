import atexit
import typing as t
from contextlib import contextmanager
from string.templatelib import Interpolation, Template
from threading import RLock

import mariadb

from ..utils import text
from . import secret, typed
from .simple_orm import Arg, Args, BaseModel, BaseModelMeta, Column, Raw, Rows

# CONVERTER: Final[dict[int, Callable[[Any], Any]]] = {
#     # mariadb.FIELD_TYPE.JSON: lambda json_str: json.loads(json_str),
#     # mariadb.FIELD_TYPE.BLOB: lambda blob: pickle.loads(blob)
# }


__CONNECTION_DATA: dict[str, t.Any] = {
    **secret.listen().DB_CONNECTION_INFO,
    **{"autocommit": False},
}

type InterpolationExecuteT = Interpolation[
    Arg.ArgPlaceholder | Raw | BaseModelMeta | Column
]
INTERPOLATION_EXECUTE = t.get_args(InterpolationExecuteT.__value__)[0]

type InterpolationExecuteManyT = Interpolation[
    Args.ArgsPlaceholder | Raw | BaseModelMeta | Column
]
INTERPOLATION_EXECUTE_MANY = t.get_args(InterpolationExecuteManyT.__value__)[0]


class CursorWrapper:
    def __init__(self, cursor: mariadb.Cursor) -> None:
        self._cursor = cursor

    def execute(
        self,
        statement: t.Callable[[Arg], Template[*tuple[InterpolationExecuteT, ...]]],
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
        statement: t.Callable[[Args], Template[*tuple[InterpolationExecuteManyT, ...]]],
        /,
    ) -> None:
        args = Args()
        template = statement(args)

        for v in template.values:
            if not isinstance(v, INTERPOLATION_EXECUTE_MANY):
                raise TypeError()

        self._cursor.executemany(text.t_to_f_string(template), args.steal())

    def fetchone[T: BaseModel](self, model: type[T]) -> T | None:
        row: dict[str, t.Any] | None = self._cursor.fetchone()

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
        id: int | t.Any = self._cursor.lastrowid

        if isinstance(id, int):
            return id

        raise LookupError

    @property
    def connection(self) -> mariadb.Connection:
        return self._cursor.connection

    def execute_raw(self, statement: str, /) -> None:
        self._cursor.execute(statement)


CONNECTION_POOL = mariadb.ConnectionPool(
    pool_name="pool",
    pool_size=5,
    pool_reset_connection=True,
    db=typed.DATABASE_NAME,
    **__CONNECTION_DATA,
)
atexit.register(lambda **_: CONNECTION_POOL.close())


@contextmanager
def connected(c: CursorWrapper | None = None, *, no_db: bool = False) -> t.Iterator[CursorWrapper]:
    if c is not None:
        yield c
        return
    
    if no_db:
        conn = mariadb.connect(**__CONNECTION_DATA)
    else:
        conn = CONNECTION_POOL.get_connection()

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SET SESSION TRANSACTION ISOLATION LEVEL REPEATABLE READ")
        yield CursorWrapper(cursor)
    except Exception as e:
        if conn:
            conn.rollback()

        raise e
    finally:
        if conn is not None:
            conn.commit()
            cursor.close()
            conn.close()
