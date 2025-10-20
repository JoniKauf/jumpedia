from dataclasses import dataclass
import enum
import typing as t


class Comparer(enum.StrEnum):
    EQ = '='
    NEQ = '<>'

class Order(enum.StrEnum):
    ASC = enum.auto()
    DESC = enum.auto()


@t.dataclass_transform(eq_default=False)
class QueryMeta(type):
    def __new__(mcls, name: str, bases: tuple[type, ...], namespace: dict[str, t.Any], /, **kwds: t.Any):
        cls = super().__new__(mcls, name, bases, namespace, **kwds)
        return dataclass(eq=False)(cls)