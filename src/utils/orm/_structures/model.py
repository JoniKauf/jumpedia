import annotationlib
import string
import typing as t
from types import SimpleNamespace

from .._utils import SqlString
from .column import Column


@t.final
class SNAKE:
    def __init__(self) -> t.Never:
        raise NotImplementedError()


@t.final
class EXACT:
    def __init__(self) -> None:
        raise NotImplementedError()


class _ModelMeta(type, SqlString):
    _table_name: str
    _columns: list[Column[t.Any, t.Any]]

    def _sql_str(self) -> str:
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
    _columns_data: dict[str, t.Any]

    @t.final
    def __init_subclass__(cls, table_name: str | type[SNAKE] | type[EXACT]) -> None:
        if cls.__bases__ != (Model,):
            raise RuntimeError

        if table_name is SNAKE:
            table_name = cls.__name__.translate(_SNAKE_TRANS_TABLE).removeprefix("_")
        elif table_name is EXACT:
            table_name = cls.__name__

        cls._table_name = table_name

    @t.final
    def __init__(self, data: t.Mapping[str, t.Any]) -> None:
        self._columns_data = {**data}
