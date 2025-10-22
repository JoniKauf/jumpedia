import string
import typing as t

import annotationlib

from .._utils import TagSafeSqlStr
from .column import Column


@t.final
class SNAKE:
    def __init__(self) -> t.Never:
        raise NotImplementedError()


class _ModelMeta(type, TagSafeSqlStr):
    _table_name: str
    _columns: list[Column[t.Any]]

    def __str__(self) -> str:
        return f"`{self._table_name}`"


_SNAKE_TRANS_TABLE = str.maketrans(
    {
        c_up: f"_{c_low}"
        for c_up, c_low in zip(string.ascii_uppercase, string.ascii_lowercase)
    }
)


class Model(metaclass=_ModelMeta):
    _columns_data: dict[str, t.Any]

    @t.final
    def __init_subclass__(cls, table_name: str | type[SNAKE]) -> None:
        if table_name is SNAKE:
            table_name = cls.__name__.translate(_SNAKE_TRANS_TABLE).removeprefix("_")

        cls._table_name = table_name

        new_annotations: dict[str, t.Any] = {}

        mro = cls.mro()

        # Iterate over mro in reverse, starting from direct subclass of Model to more specialized
        for base in reversed((cls, *mro[:mro.index(Model)])):
            new_annotations.update(
                annotationlib.get_annotations(base, format=annotationlib.Format.VALUE)
            )

        cls.__annotations__ = new_annotations

        for name, anno in new_annotations.items():
            if (
                t.get_origin(anno) is not Column
                or len(anno_args := t.get_args(anno)) != 1
            ):
                raise ValueError(
                    f"Field {name!r} of class {cls.__name__!r} is not annotated as {Column.__name__}[<type>]"
                )

            col = Column(cls, name, anno_args[0])
            setattr(cls, name, col)

    @t.final
    def __init__(self, data: t.Mapping[str, t.Any]) -> None:
        if data.keys() != self.__class__.__annotations__.keys():
            raise ValueError

        self._columns_data = {**data}


__all__ = ["Model", "SNAKE"]
