from typing import AbstractSet, Any, Callable, ClassVar, Generator, Mapping, Self, Sequence, final, overload
from typing_extensions import TypeForm

from utils import text

def quoted(s: str) -> str:
    return f'`{s}`'

class Column[TOwner: BaseModel, TValue: Any]:
    @overload
    def __init__(self, type: type[TValue], func: Callable[[TOwner], Any]) -> None:
        pass

    @overload
    def __init__(self, type: tuple[type[TValue], ...], func: Callable[[TOwner], Any]) -> None:
        pass
    
    def __init__(self, type: type[TValue] | tuple[type[TValue], ...], func: Callable[[TOwner], Any]) -> None:
        self._name: str = ''
        self._type = type
        self._func = func
        self._aliases: set[str] = set()

    def __set_name__(self, owner: type[TOwner], name: str) -> None:
        if not self._name:
            self._name = name
            owner.__columns__[name] = self
        else:
            self._aliases.add(name)

    @overload
    def __get__(self, instance: TOwner, owner: type[TOwner]) -> TValue:
        pass

    @overload
    def __get__(self, instance: None, owner: type[TOwner]) -> Self:
        pass
    
    def __get__(self, instance: TOwner | None, owner: type[TOwner]):
        if instance is None:
            return self
        
        return instance.__columns_data__[self._name]
    
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
    

type _ColumnReturnT[TOwner: BaseModel, TValue: Any] = Callable[[Callable[[TOwner], Any]], Column[TOwner, TValue]]


@overload
def column[TOwner: BaseModel, TValue: Any](type: type[TValue]) -> _ColumnReturnT[TOwner, TValue]:
    pass

@overload
def column[TOwner: BaseModel, TValue: Any](type: tuple[type[TValue], ...]) -> _ColumnReturnT[TOwner, TValue]:
    pass

def column[TOwner: BaseModel, TValue: Any](type: type[TValue] | tuple[type[TValue], ...]) -> _ColumnReturnT[TOwner, TValue]:
    def wrapper(func: Callable[[TOwner], Any]) -> Column[TOwner, TValue]:
        return Column(type, func)
    
    return wrapper

def column_alias[TOwner: BaseModel, TValue: Any](column: Column[TOwner, TValue]):
    def wrapper(func: Callable[[TOwner], Any]) -> Column[TOwner, TValue]:
        return column
    
    return wrapper

@final
class SNAKE: pass

class BaseModelMeta(type):
    __table_name__: str | None

    @classmethod
    def __prepare__(cls, name: str, bases: tuple[type, ...], table_name: str | type[SNAKE] | None):
        return {'__columns__': {}}
    
    def __new__(cls, name: str, bases: tuple[type, ...], namespace: dict[str, Any], *, table_name: str | type[SNAKE] | None) -> type:
        if table_name is SNAKE:
            table_name = text.pascal_to_snake(name)

        namespace['__table_name__'] = table_name
        return super().__new__(cls, name, bases, namespace)
    
    def __str__(self) -> str:
        if self.__table_name__ is None:
            raise RuntimeError()
        
        return quoted(self.__table_name__)
    

class BaseModel(metaclass=BaseModelMeta, table_name=None):
    __columns__: ClassVar[dict[str, Column[Self, Any]]]

    def __init__(self, columns_data: Mapping[str, Any], /, *, key_check: bool = True) -> None:
        if key_check:
            self._key_check(columns_data)
        
        self._key_checked = key_check
        self.__columns_data__ = dict(columns_data)

    @classmethod
    def _key_check(cls, columns_mapping: Mapping[str, Any]) -> None:
        if columns_mapping.keys() != cls.__columns__.keys():
            raise ValueError

    @classmethod
    def all_columns_except(cls, except_: AbstractSet[Column[Self, Any]]) -> str:
        return ','.join(
            str(c) for c in cls.__columns__.values()
            if c not in except_
        )
    
    def __init_subclass__(cls) -> None:
        if cls.__new__ != BaseModel.__new__ or cls.__init__ != BaseModel.__init__:
            raise RuntimeError

    def __repr__(self) -> str:
        cls_name = self.__class__.__name__
        args = str(self._key_checked)
        kwargs = ''.join(f", {k!r}={v!r}" for k, v in self.__columns_data__)
        
        return f"{cls_name}({args}{kwargs})"

class Rows[T: BaseModel]:
    def __init__(self, rows: Sequence[Mapping[str, Any]], model: type[T]) -> None:
        self._rows = tuple(model(row, key_check=False) for row in rows)

    
    def __iter__(self) -> Generator[T, None, None]:
        yield from self._rows 

    def __getitem__(self, idx: int) -> T:
        return self._rows[idx]

class Arg:
    placeholder: ClassVar[str] = '?'

    def __init__(self) -> None:
        self._args: list[Any] = []

    def __call__(self, o: Any) -> str:
        self.add(o)
        return self.__class__.placeholder

    def add(self, o: Any):
        self._args.append(o)

    def steal(self) -> tuple[Any, ...]:
        args = tuple(self._args)
        self._args.clear()
        return args