import annotationlib
from ast import Tuple
from re import S
import string
import typing as t

from ._query._insert import ColumnBinded, Insert
from ._query._select import Select

class _SqlStrTag:
    pass 

    
@t.final
class SNAKE: 
    def __init__(self) -> t.Never:
        raise NotImplementedError()
    

class _BaseModelMeta(type, _SqlStrTag):
    _table_name: str
    _columns: list[Column[t.Any]]

    def __str__(self) -> str:
        return f'`{self._table_name}`'

class BaseModel(metaclass=_BaseModelMeta):
    _SNAKE_TRANS_TABLE = str.maketrans({
        c_up: f'_{c_low}' for c_up, c_low in zip(string.ascii_uppercase, string.ascii_lowercase)
    })

    @t.final
    def __init_subclass__(cls, table_name: str | type[SNAKE] = SNAKE) -> None:
        if table_name is SNAKE:
            table_name = cls.__name__.translate(cls._SNAKE_TRANS_TABLE).removeprefix('_')

        cls._table_name = table_name
        
        new_annotations: dict[str, t.Any] = {}

        for base in (cls, *cls.__bases__):
            if base is BaseModel:
                break

            new_annotations.update(annotationlib.get_annotations(base, format=annotationlib.Format.VALUE))

        cls.__annotations__ = new_annotations
        cls._columns = []

        for name, anno in new_annotations.items():
            if not t.get_origin(anno) is Column:
                raise RuntimeError
            
            col = Column(cls, name, t.get_args(anno)[0])

            cls._columns.append(col)
            setattr(cls, name, col)
        
    @t.final
    def __init__(self, data: t.Mapping[str, t.Any]) -> None:
        if data.keys() != self.__class__.__annotations__.keys():
            raise ValueError
        
        self.__dict__.update(data)

    def select(self, column: Column[t.Any], /, *columns: Column[t.Any]) -> Select:
        return Select(self, (column, *columns))
    
    def select_all(self) -> Select:
        return Select(self, ())
    
    def insert(self, column_binded: ColumnBinded, /, *columns_binded: ColumnBinded) -> Insert:
        return Insert(self, (column_binded, *columns_binded))


class Column[T](_SqlStrTag):
    def __init__(self, owner: type[BaseModel], name: str, type: type[T]) -> None:
        self._owner = owner
        self._name = name
        self._type = type

    @t.overload
    def __get__(self, instance: BaseModel, owner: type[BaseModel]) -> T:
        pass

    @t.overload
    def __get__(self, instance: None, owner: type[BaseModel]) -> t.Self:
        pass
    
    def __get__(self, instance: BaseModel | None, owner: type[BaseModel]) -> t.Self | T:
        if instance is None:
            return self
        
        return getattr(instance, self._name)
    
    def __str__(self) -> str:
        return f'{self._owner}.`{self._name}`'

    def bind(self, insert: T, /, *inserts: T) -> ColumnBinded[T]:
        return ColumnBinded(self, (insert, *inserts))
 

class Task(BaseModel):
    name: Column[str]
    difficulty: Column[int]


task = Task({'name': "hi", 'difficulty': 10})

x = task.insert(Task.name.bind())