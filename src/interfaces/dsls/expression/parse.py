import enum
import logging
import typing as t
from dataclasses import dataclass

from interfaces.dsls.core.errors.parse import DepthLimitSurpassed, UnexpectedToken
from interfaces.dsls.core.lex import Token, TokenType
from interfaces.dsls.core.parse import (
    BaseParser,
    ExprNode,
    IdentifierNode,
    PushbackTokenStream,
    StringNode,
)
from interfaces.dsls.core.value_objects import Span

logger = logging.getLogger(__name__)


class BoolOpType(enum.Enum):
    AND = enum.auto()
    OR = enum.auto()


class BinOpType(enum.Enum):
    IS = enum.auto()
    IS_NOT = enum.auto()
    LT = enum.auto()
    LTE = enum.auto()
    GT = enum.auto()
    GTE = enum.auto()
    ADD = enum.auto()
    SUB = enum.auto()


@dataclass(frozen=True, slots=True)
class BinOp(ExprNode):
    type: BinOpType
    left: ExprNode
    right: ExprNode


@dataclass(frozen=True, slots=True)
class BoolOp(ExprNode):
    type: BoolOpType
    elements: tuple[ExprNode, ...]


@dataclass(frozen=True, slots=True)
class ConditionalExpr(ExprNode):
    condition: ExprNode
    true_value: ExprNode
    false_value: ExprNode


def _try_consume_token(tokens: PushbackTokenStream, type: TokenType) -> Token | None:
    tok = tokens.peek()

    if tok.type is type:
        tokens.pop()
        return tok

    return None


class ExpressionParser(BaseParser):
    def __init__(self, s: str, max_depth: int) -> None:
        super().__init__(s)
        self._max_depth = max_depth
        self._depth = 0

    def parse(self, tokens: t.Iterable[Token]) -> ExprNode:
        logger.info(self.parse.__qualname__)

        stream = PushbackTokenStream(tokens)

        result = self._parse_expr(stream)

        tok = stream.pop()

        if tok.type is not TokenType.NONE:
            raise UnexpectedToken(self._s, (TokenType.NONE,), tok)

        return result

    def _parse_expr(self, tokens: PushbackTokenStream) -> ExprNode:
        self._depth += 1
        logger.info(f"{self._parse_expr.__qualname__} (depth = {self._depth})")

        try:
            if self._depth > self._max_depth:
                raise DepthLimitSurpassed(self._s, tokens.peek(), self._max_depth)

            return self._parse_conditional(tokens)
        finally:
            self._depth -= 1

    def _parse_conditional(self, tokens: PushbackTokenStream) -> ExprNode:
        logger.info(self._parse_conditional.__qualname__)

        true_value = self._parse_or(tokens)

        if not _try_consume_token(tokens, TokenType.IF):
            return true_value

        condition = self._parse_or(tokens)

        else_tok = tokens.pop()

        if else_tok.type is not TokenType.ELSE:
            raise UnexpectedToken(self._s, (TokenType.ELSE,), else_tok)

        false_value = self._parse_conditional(tokens)

        return ConditionalExpr(
            Span(true_value.span.begin, false_value.span.end),
            condition,
            true_value,
            false_value,
        )

    def _parse_or(self, tokens: PushbackTokenStream) -> ExprNode:
        logger.info(self._parse_or.__qualname__)

        elements: list[ExprNode] = [self._parse_and(tokens)]

        while _try_consume_token(tokens, TokenType.OR):
            elements.append(self._parse_and(tokens))

        if len(elements) == 1:
            return elements[0]

        assert len(elements) > 1

        return BoolOp(
            Span(elements[0].span.begin, elements[-1].span.end),
            BoolOpType.OR,
            tuple(elements),
        )

    def _parse_and(self, tokens: PushbackTokenStream) -> ExprNode:
        logger.info(self._parse_and.__qualname__)

        elements: list[ExprNode] = [self._parse_comparison(tokens)]

        while _try_consume_token(tokens, TokenType.AND):
            elements.append(self._parse_comparison(tokens))

        if len(elements) == 1:
            return elements[0]

        assert len(elements) > 1

        return BoolOp(
            Span(elements[0].span.begin, elements[-1].span.end),
            BoolOpType.AND,
            tuple(elements),
        )

    def _parse_comparison(self, tokens: PushbackTokenStream) -> ExprNode:
        logger.info(self._parse_comparison.__qualname__)

        left = self._parse_additive(tokens)

        if _try_consume_token(tokens, TokenType.IS):
            op_type = (
                BinOpType.IS_NOT
                if _try_consume_token(tokens, TokenType.NOT)
                else BinOpType.IS
            )

            right = self._parse_additive(tokens)

            return BinOp(
                Span(left.span.begin, right.span.end),
                op_type,
                left,
                right,
            )

        tok = tokens.peek()

        for tok_type, bin_op_type in (
            (TokenType.LT, BinOpType.LT),
            (TokenType.LTE, BinOpType.LTE),
            (TokenType.GT, BinOpType.GT),
            (TokenType.GTE, BinOpType.GTE),
        ):
            if tok.type != tok_type:
                continue

            tokens.pop()
            right = self._parse_additive(tokens)

            return BinOp(
                Span(left.span.begin, right.span.end),
                bin_op_type,
                left,
                right,
            )

        return left

    def _parse_additive(self, tokens: PushbackTokenStream) -> ExprNode:
        logger.info(self._parse_additive.__qualname__)

        left = self._parse_atom(tokens)

        while tokens.peek().type in (TokenType.PLUS, TokenType.MINUS):
            op = tokens.pop()
            right = self._parse_atom(tokens)

            left = BinOp(
                Span(left.span.begin, right.span.end),
                BinOpType.ADD if op.type is TokenType.PLUS else BinOpType.SUB,
                left,
                right,
            )

        return left

    def _parse_atom(self, tokens: PushbackTokenStream) -> ExprNode:
        logger.info(self._parse_atom.__qualname__)

        tok = tokens.pop()

        match tok.type:
            case TokenType.IDENT:
                return IdentifierNode(tok.span, tok.value)

            case TokenType.STRING:
                return StringNode(tok.span, tok.value)

            case TokenType.LPAREN:
                expr = self._parse_expr(tokens)

                closing = tokens.pop()

                if closing.type != TokenType.RPAREN:
                    raise UnexpectedToken(self._s, (TokenType.RPAREN,), closing)

                return expr

        raise UnexpectedToken(
            self._s, (TokenType.IDENT, TokenType.STRING, TokenType.LPAREN), tok
        )
