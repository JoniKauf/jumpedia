from dataclasses import dataclass

from interfaces.dsls.core.errors.base import DslError
from interfaces.dsls.expression.parse import BinOp, BinOpType

lazy from interfaces.dsls.core.parse import ExprNode


type AnyEvalErrorT = UnexpectedNode | UnexpectedBinOp | EmptyAfterNonEqualityOperator

@dataclass()
class EvalError(DslError):
    """Base class of all errors that occur in the evaluaton phase."""

    s: str


@dataclass()
class UnexpectedNode(EvalError):
    expected: tuple[type[ExprNode], ...]
    received: ExprNode


@dataclass()
class UnexpectedBinOp(EvalError):
    expected: tuple[BinOpType, ...]
    received: BinOpType


@dataclass()
class EmptyAfterNonEqualityOperator(EvalError):
    received: BinOp
