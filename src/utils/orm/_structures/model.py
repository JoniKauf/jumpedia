import string
import typing as t
from types import SimpleNamespace

from .. import _utils
from .._query.delete import Delete
from .._query.insert import Insert
from .._query.select import Select
from .._query.update import Update
from .column import Column, ColumnBind, ColumnSet


@t.final
class SNAKE:
    def __init__(self) -> t.Never:
        raise NotImplementedError()


@t.final
class EXACT:
    def __init__(self) -> None:
        raise NotImplementedError()


class _ModelMeta(type, _utils.SqlString):
    _table_name: str

    def __str__(self) -> str:
        return f"`{self._table_name}`"


_SNAKE_TRANS_TABLE = str.maketrans(
    {
        c_up: f"_{c_low}"
        for c_up, c_low in zip(string.ascii_uppercase, string.ascii_lowercase)
    }
)

if t.TYPE_CHECKING:
    _ModelBase = SimpleNamespace
else:
    _ModelBase = object


class Model(_ModelBase, metaclass=_ModelMeta):
    _columns: t.ClassVar[tuple[Column[t.Self, t.Any], ...]]
    _columns_data: t.Final[dict[str, t.Any]]

    @t.final
    def __init_subclass__(cls, table_name: str | type[SNAKE] | type[EXACT]) -> None:
        if cls.__bases__ != (Model,):
            raise RuntimeError

        if table_name is SNAKE:
            table_name = cls.__name__.translate(_SNAKE_TRANS_TABLE).removeprefix("_")
        elif table_name is EXACT:
            table_name = cls.__name__

        _utils.validate_identifier(table_name)

        cls._table_name = table_name
        cls._columns = tuple(
            obj for obj in cls.__dict__.values() if isinstance(obj, Column)
        )

    @t.final
    def __init__(self, data: t.Mapping[str, t.Any]) -> None:
        self._columns_data = {**data}

    # --- Queries ---

    @t.overload
    @classmethod
    def select(
        cls, all: t.Literal["*"], /
    ) -> Select[t.Self]:
        pass

    @t.overload
    @classmethod
    def select(
        cls, column: Column[t.Self, t.Any], /, *columns: Column[t.Self, t.Any]
    ) -> Select[t.Self]:
        pass

    @classmethod
    def select[T: Model](
        cls,
        all_or_column: Column[t.Self | T, t.Any] | t.Literal["*"],
        /,
        *columns: Column[t.Self | T, t.Any]
    ) -> Select[t.Self | T]:
        cols: tuple[Column[t.Self | T, t.Any], ...] = ()

        if isinstance(all_or_column, Column):
            cols = (all_or_column, *columns)

        return Select(cls, cols, [], (), None)  # type: ignore

    @classmethod
    def insert(
        cls,
        column_binded: ColumnBind[t.Self, t.Any],
        /,
        *columns_binded: ColumnBind[t.Self, t.Any],
        ignore: bool = False,
    ) -> Insert[t.Self]:
        return Insert(cls, ((column_binded, *columns_binded), ignore))

    @classmethod
    def update(
        cls,
        column_set: ColumnSet[t.Self, t.Any],
        /,
        *columns_set: ColumnSet[t.Self, t.Any],
        ignore: bool = False,
    ) -> Update[t.Self]:
        return Update(cls, ((column_set, *columns_set), ignore), [], (), None)

    @classmethod
    def delete(cls, *, ignore: bool = False) -> Delete[t.Self]:
        return Delete(cls, ignore, [], (), None)


__all__ = ["SNAKE", "EXACT", "Model"]
