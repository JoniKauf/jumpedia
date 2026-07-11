from dataclasses import dataclass

from interfaces.dsls.expression.parse import BinOpType
from interfaces.dsls.shared.errors.base import DslError
lazy from interfaces.dsls.shared.parse import ExprNode

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