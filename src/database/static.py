


import enum
from typing import Any, Callable, Iterator, Never, Sequence, final, overload


class KeyCheck(enum.Enum):
    NONE = enum.auto()
    FIRST = enum.auto()
    ALL = enum.auto()


class Column:
    def __init__(self, name: str) -> None:
        self.name = name
    
    def __str__(self) -> str:
        return f'`{self.name}`'


class BaseRowMeta(type):
    def __str__(self) -> str:
        return f"`{self.__name__}`"
    
        
class BaseRow(metaclass=BaseRowMeta):
    __required_keys__: set[str] = set()
    __extra_keys__: set[str] = set()

    def __init__(self, row: dict[str, Any], key_check: bool = True) -> None:
        if self.__class__ == BaseRow:
            raise RuntimeError
        
        if key_check and self.__required_keys__ != row.keys():
            raise KeyError(set(row), self.__required_keys__)
        
        self.__mapping__ = row


@final
class Rows[T: BaseRow]:
    def __init__(self, rows_data: Sequence[dict[str, Any]], row_type: type[T], key_check: KeyCheck = KeyCheck.FIRST) -> None:
        self.row_type = row_type 

        if not rows_data:
            self.rows = ()
            return
        
        if key_check is not KeyCheck.NONE:
            if key_check is KeyCheck.FIRST:
                rows_data = (rows_data[0],)
            
            for row in rows_data:
                for key in row:
                    if row_type. row_type.__required_keys__

        self.rows = tuple(map(lambda row_data: row_type(row_data, False), rows_data))

    def __iter__(self) -> Iterator[T]:
        yield from self.rows


class Cell[TRow: BaseRow, TValue: Any]:
    def __init__(self, wrapped: Callable[[TRow], TValue] | Callable[[type[TRow]], TValue], extra: bool):
        self.__wrapped__ = wrapped
        self.extra = extra
    
    def __set_name__(self, owner: type[TRow], name: str):
        self.name = name
        self.column = Column(name)

        if not owner.__required_keys__:
            owner.__required_keys__ = set()
            owner.__extra_keys__ = set()

        if self.extra:
            owner.__extra_keys__.add(name)
        else:
            owner.__required_keys__.add(name)

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

class FakeCell[TOwner: BaseRow, TValue: Any]:
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