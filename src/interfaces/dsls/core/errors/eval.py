from dataclasses import dataclass

from domain.value_objects.filter import OpType
from interfaces.dsls.expression.parse import BinOp, BinOpType
from interfaces.dsls.core.errors.base import DslError
lazy from interfaces.dsls.core.parse import ExprNode

@dataclass(frozen=True, slots=True)
class EvalError(DslError):
    """Base class of all errors that occur in the evaluaton phase."""

    s: str

@dataclass(frozen=True, slots=True)
class UnexpectedNode(EvalError):
    expected: tuple[type[ExprNode], ...]
    received: ExprNode

@dataclass(frozen=True, slots=True)
class UnexpectedBinOp(EvalError):
    expected: tuple[BinOpType, ...]
    received: BinOpType

@dataclass(frozen=True, slots=True)
class EmptyAfterNonEqualityOperator(EvalError):
    received: BinOp