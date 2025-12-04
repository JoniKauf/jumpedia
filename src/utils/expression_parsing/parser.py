import ast
import io
import tokenize
import typing as t
from dataclasses import KW_ONLY, InitVar, dataclass

from . import errors
from .visitor import BaseExpressionVisitor, ExpressionVisitorConfig


class ExpressionParserConfig(t.NamedTuple):
    SOURCE_LEN_MAX: int
    TOKEN_COUNT_MAX: int


@dataclass(frozen=True, slots=True)
class ExpressionParser[T, **P]:
    visitor: BaseExpressionVisitor[T, P]
    _: KW_ONLY
    config: ExpressionParserConfig

    def _validate_tokens(self, s: str):
        tok_gen = tokenize.generate_tokens(io.StringIO(s).readline)
        prev_tok = next(tok_gen, None)

        if prev_tok is None:
            return

        if self.config.TOKEN_COUNT_MAX < 1:
            raise errors.MaxTokenCountExceecedError()

        count = 1

        for tok in tok_gen:
            count += 1

            if count > self.config.TOKEN_COUNT_MAX:
                raise errors.MaxTokenCountExceecedError()

            # Disallow inplicit string concat
            if prev_tok.type == tokenize.STRING and tok.type == tokenize.STRING:
                raise errors.ImplicitConcatOfStringsError(prev_tok.string, tok.string)

            prev_tok = tok

    def parse(self, s: str, *args: P.args, **kwargs: P.kwargs) -> T:
        if not (s := s.strip()):
            raise errors.EmptySrcError()

        if "\n" in s:
            raise errors.NewlineInSrcError()

        if len(s) > self.config.SOURCE_LEN_MAX:
            raise errors.MaxSrcLengthExceededError()

        # Throws TokenError when syntax wrong
        self._validate_tokens(s)

        return self.visitor.start_visit(ast.parse(s, mode="eval"), *args, **kwargs)
