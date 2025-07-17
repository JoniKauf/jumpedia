


from typing import Any, Callable, Iterable, Iterator, Never, Self, Sequence, final, get_args, get_type_hints, overload
from utils import text

class AUTO_SNAKE: pass

class Column:
    def __init__(self, name: str) -> None:
        self.name = name
    
    def __str__(self) -> str:
        return f'`{self.name}`'


class BaseRowMeta(type):
    __columns__: list[Column]
    __table_name__: str | None

    def __new__(cls, name: str, bases: tuple[type, ...], namespace: dict[str, Any], *, table_name: str | type[AUTO_SNAKE] | None) -> type:
        namespace['__columns__'] = []

        if table_name is AUTO_SNAKE:
            table_name = text.pascal_to_snake(name)
        
        namespace['__table_name__'] = table_name

        return super().__new__(cls, name, bases, namespace)

    def __str__(cls) -> str:
        if cls.__table_name__ is None:
            raise NotImplementedError("Not stringifiable because no table_name given")
        
        return f"`{cls.__table_name__}`"
    
    def __pos__(cls) -> str:
        return ','.join(str(col) for col in cls.__columns__)
    
        
class BaseRow(metaclass=BaseRowMeta, table_name=None):
    def __init__(self, row: dict[str, Any]) -> None:
        if self.__class__ == BaseRow:
            raise RuntimeError
        
        self.__mapping__ = row

    @overload
    @classmethod
    def get_optional(cls, row: None) -> None:
        pass

    @overload
    @classmethod
    def get_optional(cls, row: dict[str, Any]) -> Self:
        pass

    @classmethod
    def get_optional(cls, row: dict[str, Any] | None) -> None | Self:
        if row is None:
            return None
        
        return cls(row)

@final
class Rows[T1: BaseRow]:
    def __init__(self, rows_data: Iterable[dict[str, Any]], row_type: type[T1]) -> None:
        self.row_type = row_type 

        if not rows_data:
            self.rows = ()
            return

        self.rows = tuple(map(lambda row_data: row_type(row_data), rows_data))

    def __iter__(self) -> Iterator[T1]:
        yield from self.rows

    def __len__(self) -> int:
        return len(self.rows)
    
    def __getitem__(self, index: int) -> T1:
        return self.rows[index]


class Cell[TRow: BaseRow, TValue: Any]:
    def __init__(self, wrapped: Callable[[TRow], TValue] | Callable[[type[TRow]], TValue]) -> None:
        self.__wrapped__ = wrapped
    
    def __set_name__(self, owner: type[TRow], name: str) -> None:
        self.name = name
        self.column = Column(name)
        owner.__columns__.append(self.column)

    @overload
    def __get__(self, instance: TRow, owner: type[TRow]) -> TValue:
        pass
    
    @overload
    def __get__(self, instance: None, owner: type[TRow]) -> Column:
        pass

    def __get__(self, instance: TRow | None, owner: type[TRow]) -> TValue | Column:
        if instance is None:
            return self.column
        
        return instance.__mapping__[self.name] 
    
    def __set__(self, instance: TRow, value: TValue) -> None:
        instance.__mapping__[self.name] = value

class CellAlias[TOwner: BaseRow, TValue: Any]:
    def __init__(self, wrapped: Callable[[TOwner], TValue] | Callable[[type[TOwner]], Column]):
        self.__wrapped__ = wrapped

    @overload
    def __get__(self, instance: TOwner, owner: type[TOwner]) -> TValue:
        pass
    
    @overload
    def __get__(self, instance: None, owner: type[TOwner]) -> Column:
        pass

    def __get__(self, instance: TOwner | None, owner: type[TOwner]) -> TValue | Column:
        return self.__wrapped__(instance or owner)  # type: ignore


def cell_body() -> Never:
    raise RuntimeError(
        "This function should not be called, "
        "because it should only be the body of a Cell!"
    )