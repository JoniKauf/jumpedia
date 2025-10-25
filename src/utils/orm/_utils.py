import typing as t

type TupleOfOneOrMore[T] = tuple[T, *tuple[T, ...]]


@t.runtime_checkable
class SqlString(t.Protocol):
    def _sql_str(self) -> str:
        ...
