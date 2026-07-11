import enum
from dataclasses import dataclass

from domain.value_objects.attribute import AttributeSynStr
from domain.value_objects.field_slot import FieldSlotStr


class OpType(enum.Enum):
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
    """Guarantees that value is only EMPTY for EQ and NEQ operators."""
    attribute: AttributeSynStr
    operator: OpType
    value: FieldSlotStr | EMPTY


@dataclass(frozen=True, slots=True)
class AndFilter(Filter):
    operands: tuple[Filter, ...]


@dataclass(frozen=True, slots=True)
class OrFilter(Filter):
    operands: tuple[Filter, ...]
