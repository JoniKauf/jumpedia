


from abc import abstractmethod
import enum
from typing import Any, Callable, Iterator, MutableMapping, Never, Sequence, final, overload

class Column:
    def __init__(self, name: str) -> None:
        self.name = name
    
    def __str__(self) -> str:
        return f'`{self.name}`'


class BaseRowMeta(type):
    def __str__(self) -> str:
        return f"`{self.__name__}`"
    
        
class BaseRow(metaclass=BaseRowMeta):
    def __init__(self, row: dict[str, Any]) -> None:
        if self.__class__ == BaseRow:
            raise RuntimeError
        
        self.__mapping__ = row


@final
class Rows[T1: BaseRow]:
    def __init__(self, rows_data: Sequence[dict[str, Any]], row_type: type[T1]) -> None:
        self.row_type = row_type 

        if not rows_data:
            self.rows = ()
            return

        self.rows = tuple(map(lambda row_data: row_type(row_data), rows_data))

    def __iter__(self) -> Iterator[T1]:
        yield from self.rows


class Cell[TRow: BaseRow, TValue: Any]:
    def __init__(self, wrapped: Callable[[TRow], TValue] | Callable[[type[TRow]], TValue]):
        self.__wrapped__ = wrapped
    
    def __set_name__(self, owner: type[TRow], name: str):
        self.name = name
        self.column = Column(name)

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