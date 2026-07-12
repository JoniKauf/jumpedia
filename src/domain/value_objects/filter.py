import enum
from dataclasses import dataclass

from domain.value_objects.attribute import AttributeSynStr
from domain.value_objects.field_slot import FieldSlotStr
import typing as t


class OpType(enum.Enum):
    EQ = enum.auto()
    NEQ = enum.auto()
    LT = enum.auto()
    LTE = enum.auto()
    GT = enum.auto()
    GTE = enum.auto()


type FilterT = OrFilter | AndFilter | EmptyComparisonFilter | NonEmptyComparisonFilter


@dataclass(frozen=True, slots=True)
class NonEmptyComparisonFilter:
    attribute: str
    op: OpType
    value: str


@dataclass(frozen=True, slots=True)
class EmptyComparisonFilter:
    attribute: str
    op: t.Literal[OpType.EQ, OpType.NEQ]


@dataclass(frozen=True, slots=True)
class AndFilter:
    operands: tuple[FilterT, ...]


@dataclass(frozen=True, slots=True)
class OrFilter:
    operands: tuple[FilterT, ...]
