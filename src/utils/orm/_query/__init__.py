import enum
import typing as t
from abc import ABCMeta, abstractmethod
from dataclasses import dataclass

if t.TYPE_CHECKING:
    from .._structures.cursor import Cursor
    from .._structures.model import Model


class Operator(enum.StrEnum):
    EQ = "="
    NEQ = "<>"


class Order(enum.StrEnum):
    ASC = enum.auto()
    DESC = enum.auto()


@t.dataclass_transform(eq_default=False, frozen_default=True)
class _QueryMeta(ABCMeta):
    def __new__(
        mcls,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, t.Any],
        /,
        **kwds: t.Any,
    ):
        cls = super().__new__(mcls, name, bases, namespace, **kwds)
        return dataclass(eq=False, frozen=True)(cls)


class Query[T: Model](metaclass=_QueryMeta):
    _cursor: Cursor
    _table: type[T]

    @abstractmethod
    def _to_sql(self) -> tuple[str, list[t.Any]]:
        pass

    def _core_execute(self) -> None:
        self._cursor._mariadb_cursor.execute(*self._to_sql())


class FetchableQuery[T: Model](Query[T]):
    def fetch_one(self) -> T | None:
        self._core_execute()

        fetch = t.cast(dict[str, t.Any] | None, self._cursor._mariadb_cursor.fetchone())

        if fetch is None:
            return None

        return self._table(fetch)

    def fetch_all(self) -> list[T]:
        self._core_execute()

        fetch = t.cast(list[dict[str, t.Any]], self._cursor._mariadb_cursor.fetchone())

        return list(map(self._table, fetch))


@dataclass(frozen=True, slots=True)
class ExecuteData[T1: int | None, T2: int | None]:
    last_generated_id: T1
    affected_row_count: T2


class ExecutableQuery[T: Model](Query[T]):
    @t.overload
    def execute(
        self,
        *,
        get_last_generated_id: t.Literal[False] = False,
        get_affected_row_count: t.Literal[False] = False,
    ) -> ExecuteData[None, None]:
        pass

    @t.overload
    def execute(
        self, *, get_last_generated_id: t.Literal[True]
    ) -> ExecuteData[int | None, None]:
        pass

    @t.overload
    def execute(
        self, *, get_affected_row_count: t.Literal[True]
    ) -> ExecuteData[None, int]:
        pass

    @t.overload
    def execute(
        self,
        *,
        get_last_generated_id: t.Literal[True],
        get_affected_row_count: t.Literal[True],
    ) -> ExecuteData[int | None, int]:
        pass

    def execute(
        self,
        *,
        get_last_generated_id: bool = False,
        get_affected_row_count: bool = False,
    ) -> ExecuteData[t.Any, t.Any]:
        self._core_execute()

        match (get_last_generated_id, get_affected_row_count):
            case False, False:
                return ExecuteData(None, None)
            case True, False:
                return ExecuteData(self._cursor._mariadb_cursor.lastrowid, None)
            case False, True:
                return ExecuteData(None, self._cursor._mariadb_cursor.rowcount)
            case True, True:
                return ExecuteData(
                    self._cursor._mariadb_cursor.lastrowid,
                    self._cursor._mariadb_cursor.rowcount,
                )
            case _:
                t.assert_never((get_last_generated_id, get_affected_row_count))
