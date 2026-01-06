import ast
import io
import tokenize
import typing as t
from collections.abc import Callable
from dataclasses import KW_ONLY, dataclass

from . import errors
from .visitor import BaseExpressionVisitor


class ExpressionParserConfig(t.NamedTuple):
    SOURCE_LEN_MAX: int
    TOKEN_COUNT_MAX: int
    PRE_PROCESS: Callable[[str, ExpressionParser], str]


@dataclass(frozen=True, slots=True)
class ExpressionParser[T, **P]:
    visitor: BaseExpressionVisitor[T, P]
    _: KW_ONLY
    config: ExpressionParserConfig

    def parse(self, s: str, *args: P.args, **kwargs: P.kwargs) -> T:
        if not (s := s.strip()):
            raise errors.EmptySrcError()

        if len(s) > self.config.SOURCE_LEN_MAX:
            raise errors.MaxSrcLengthExceededError()

        try:
            s = self.config.PRE_PROCESS(s, self)
            return self.visitor.start_visit(ast.parse(s, mode="eval"), *args, **kwargs)
        except SyntaxError:
            raise errors.InvalidSyntaxError()
