


import enum
from typing import Any, Iterable, Iterator, Sequence, final
import typing_extensions
from typing import assert_never
import functools

class Check(enum.Enum):
    NONE = enum.auto()
    FIRST = enum.auto()
    ALL = enum.auto()

class Column:
    def __init__(self, s: str) -> None:
        self.name = s

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(name={self.name})'
    
    def __str__(self) -> str:
        return f'`{self.name}`'


_ANNOTATIONS = '__annotations'

class BaseRowMeta(type):
    def __new__(cls, name: str, bases: tuple[type, ...], namespace: dict[str, Any]) -> type:
        annotations = namespace.get('__annotations__', {})
        namespace.update({k: Column(k) for k in annotations})
        namespace[_ANNOTATIONS] = frozenset(annotations)

        return super().__new__(cls, name, bases, namespace)
        
class BaseRow(metaclass=BaseRowMeta):
    @classmethod
    def _get_annotations(cls) -> frozenset[str]:
        return getattr(cls, _ANNOTATIONS)
    
    def __init__(self, row: dict[str, Any], check: bool = True) -> None:
        if self.__class__ == BaseRow:
            raise RuntimeError

        if check and self.__class__._get_annotations() != frozenset(row):
            raise ValueError
        
        self.__dict__ = row

class TestRow(BaseRow):
    v: int = 10
    
print(TestRow.v)
print(TestRow({"v1": 10}).v)

TestRow.v

@final
class Rows[T: BaseRow]:
    def __init__(self, rows_data: Sequence[dict[str, Any]], row_type: type[T], check: Check = Check.FIRST) -> None:
        self.row_type = row_type 

        if not rows_data:
            self.rows = ()
            return
        
        if check is not Check.NONE:
            annotations = row_type._get_annotations()

            if check is Check.FIRST:
                if frozenset(rows_data[0]) != annotations:
                    raise ValueError
            elif check == Check.ALL:
                if not all(frozenset(row) == annotations for row in rows_data):
                    raise ValueError
            else:
                assert_never(check)

        self.rows = tuple(map(row_type, rows_data))

    def __iter__(self) -> Iterator[T]:
        yield from self.rows

