import typing as t

from typing_extensions import TypeForm

from ..utils import text


def quoted(s: str) -> str:
    return f"`{s}`"


class Column[TOwner: BaseModel, TValue: t.Any]:
    def __init__(
        self, type: TypeForm[TValue], func: t.Callable[[TOwner], t.Any]
    ) -> None:
        self._name: str = ""
        self._type = type
        self._func = func
        self._aliases: set[str] = set()

    def __set_name__(self, owner: type[TOwner], name: str) -> None:
        if not self._name:
            self._name = name
            owner._columns[name] = self
        else:
            self._aliases.add(name)

    @t.overload
    def __get__(self, instance: TOwner, owner: type[TOwner]) -> TValue:
        pass

    @t.overload
    def __get__(self, instance: None, owner: type[TOwner]) -> t.Self:
        pass

    def __get__(self, instance: TOwner | None, owner: type[TOwner]):
        if instance is None:
            return self

        return instance._columns_data[self._name]

    def __hash__(self) -> int:
        return hash((self._type, self._name))

    def __eq__(self, value: object) -> bool:
        if isinstance(value, self.__class__):
            return self._type == value._type and self._name == value._name

        return NotImplemented

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.__dict__!r})"

    def __str__(self) -> str:
        return quoted(self._name)

    def qual(self, model: type[TOwner]) -> str:
        return f"{model}.{self}"


def column[TOwner: BaseModel, TValue](
    type: TypeForm[TValue],
) -> t.Callable[[t.Callable[[TOwner], t.Any]], Column[TOwner, TValue]]:
    def wrapper(func: t.Callable[[TOwner], t.Any]) -> Column[TOwner, TValue]:
        return Column(type, func)

    return wrapper


def column_alias[TOwner: BaseModel, TValue: t.Any](column: Column[TOwner, TValue]):
    def wrapper(func: t.Callable[[TOwner], t.Any]) -> Column[TOwner, TValue]:
        return column

    return wrapper


@t.final
class SNAKE:
    pass


class BaseModelMeta(type):
    _table_name: str | None

    @classmethod
    def __prepare__(
        cls, name: str, bases: tuple[type, ...], table_name: str | type[SNAKE] | None
    ):
        return {"_columns": {}}

    def __new__(
        cls,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, t.Any],
        *,
        table_name: str | type[SNAKE] | None,
    ) -> type:
        if table_name is SNAKE:
            table_name = text.pascal_to_snake(name)

        namespace["_table_name"] = table_name
        return super().__new__(cls, name, bases, namespace)

    def __str__(self) -> str:
        if self._table_name is None:
            raise RuntimeError()

        return quoted(self._table_name)


class BaseModel(metaclass=BaseModelMeta, table_name=None):
    _columns: t.ClassVar[dict[str, Column[t.Self, t.Any]]]

    def __init__(self, columns_data: t.Mapping[str, t.Any]) -> None:
        self._columns_data = dict(columns_data)

    @classmethod
    def all_columns_except(cls, except_: t.AbstractSet[Column[t.Self, t.Any]]) -> str:
        return ",".join(str(c) for c in cls._columns.values() if c not in except_)

    def __init_subclass__(cls) -> None:
        if cls.__new__ != BaseModel.__new__ or cls.__init__ != BaseModel.__init__:
            raise RuntimeError


class Rows[T: BaseModel]:
    def __init__(self, rows: t.Sequence[t.Mapping[str, t.Any]], model: type[T]) -> None:
        self._rows = tuple(model(row) for row in rows)

    def __iter__(self) -> t.Generator[T, None, None]:
        yield from self._rows

    def __len__(self) -> int:
        return len(self._rows)

    def __getitem__(self, idx: int) -> T:
        return self._rows[idx]


PLACEHOLDER_STR = "?"


class Arg:
    class ArgPlaceholder:
        def __init__(self, value: str) -> None:
            self.value = value

        def __str__(self) -> str:
            return self.value

    def __init__(self) -> None:
        self._args: list[t.Any] = []

    def __call__(self, o: object) -> ArgPlaceholder:
        return self.add(o)

    def add(self, o: object) -> ArgPlaceholder:
        self._args.append(o)
        return self.__class__.ArgPlaceholder(PLACEHOLDER_STR)

    def steal(self) -> tuple[object, ...]:
        args = tuple(self._args)
        self._args.clear()
        return args


class Args:
    class ArgsPlaceholder:
        def __init__(self, value: str) -> None:
            self.value = value

        def __str__(self) -> str:
            return self.value

    def __init__(self) -> None:
        self._args: list[t.Sequence[t.Any]] = []

    def __call__(self, os: t.Iterable[object]) -> ArgsPlaceholder:
        return self.add(os)

    def add(self, os: t.Iterable[object]) -> ArgsPlaceholder:
        if not isinstance(os, tuple):
            os_tup: t.Sequence[object] = tuple(os)

        if self._args and len(os_tup) != len(self._args[0]):
            raise ValueError

        self._args.append(os_tup)

        return self.__class__.ArgsPlaceholder(PLACEHOLDER_STR)

    def steal(self) -> tuple[t.Sequence[object], ...]:
        args = tuple(zip(*self._args))
        self._args.clear()
        return args


class Raw:
    def __init__(self, raw: str, /) -> None:
        self.raw = raw

    def __str__(self) -> str:
        return self.raw
