import enum
from dataclasses import dataclass

from domain.entities.attribute import AttributeEntity
from domain.value_objects.field_slot import FieldSlotStr


class Op(enum.Enum):
    EQ = enum.auto()
    NEQ = enum.auto()
    LT = enum.auto()
    LTE = enum.auto()
    GT = enum.auto()
    GTE = enum.auto()


EMPTY = sentinel("EMPTY")


@dataclass(frozen=True, slots=True)
class Filter:
    pass


@dataclass(frozen=True, slots=True)
class ComparisonFilter(Filter):
    attribute: AttributeEntity
    operator: Op
    value: FieldSlotStr | EMPTY


@dataclass(frozen=True, slots=True)
class AndFilter(Filter):
    operands: tuple[Filter, ...]


@dataclass(frozen=True, slots=True)
class OrFilter(Filter):
    operands: tuple[Filter, ...]
