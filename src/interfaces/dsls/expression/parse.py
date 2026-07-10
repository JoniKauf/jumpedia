import enum
import typing as t
from dataclasses import dataclass

from interfaces.dsls.shared.errors.parse import DepthLimitSurpassed, ExpectedKeyword, UnexpectedToken
from interfaces.dsls.shared.lexing import Token, TokenType
from interfaces.dsls.shared.parsing import (
    ExprNode,
    IdentifierNode,
    PushbackTokenStream,
    StringNode,
    TextNodeT,
)
from interfaces.dsls.shared.value_objects import Span


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


class KeywordType(enum.StrEnum):
    IF = "if"
    ELSE = "else"
    IS = "is"
    NOT = "not"
    OR = "or"
    AND = "and"


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


class _Parser:
    def __init__(self, max_depth: int, error_s: str) -> None:
        self.max_depth = max_depth
        self.depth = 0
        self.error_s = error_s

    def parse_expr(self, tokens: PushbackTokenStream) -> ExprNode:
        self.depth += 1

        try:
            if self.depth > self.max_depth:
                raise DepthLimitSurpassed(self.error_s, tokens.peek(), self.max_depth)

            return self.parse_conditional(tokens)
        finally:
            self.depth -= 1

    def parse_conditional(self, tokens: PushbackTokenStream) -> ExprNode:
        true_value = self.parse_or(tokens)

        if not _try_consume_keyword(tokens, KeywordType.IF):
            return true_value

        condition = self.parse_or(tokens)

        else_tok = tokens.pop()

        if else_tok.type != TokenType.IDENT or else_tok.value != KeywordType.ELSE:
            raise ExpectedKeyword(self.error_s, (KeywordType.ELSE,), else_tok)

        false_value = self.parse_conditional(tokens)

        return ConditionalExpr(
            Span(true_value.span.begin, false_value.span.end),
            condition,
            true_value,
            false_value,
        )

    def parse_or(self, tokens: PushbackTokenStream) -> ExprNode:
        elements: list[ExprNode] = [self.parse_and(tokens)]

        while _try_consume_keyword(tokens, KeywordType.OR):
            elements.append(self.parse_and(tokens))

        if len(elements) == 1:
            return elements[0]

        assert len(elements) > 1

        return BoolOp(
            Span(elements[0].span.begin, elements[-1].span.end),
            BoolOpType.OR,
            tuple(elements),
        )

    def parse_and(self, tokens: PushbackTokenStream) -> ExprNode:
        elements: list[ExprNode] = [self.parse_comparison(tokens)]

        while _try_consume_keyword(tokens, KeywordType.AND):
            elements.append(self.parse_comparison(tokens))

        if len(elements) == 1:
            return elements[0]

        assert len(elements) > 1

        return BoolOp(
            Span(elements[0].span.begin, elements[-1].span.end),
            BoolOpType.AND,
            tuple(elements),
        )

    def parse_comparison(self, tokens: PushbackTokenStream) -> ExprNode:
        left = self.parse_additive(tokens)

        if _try_consume_keyword(tokens, KeywordType.IS):
            op_type = (
                BinOpType.IS_NOT
                if _try_consume_keyword(tokens, KeywordType.NOT)
                else BinOpType.IS
            )

            right = self.parse_additive(tokens)

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
            right = self.parse_additive(tokens)

            return BinOp(
                Span(left.span.begin, right.span.end),
                bin_op_type,
                left,
                right,
            )

        return left

    def parse_additive(self, tokens: PushbackTokenStream) -> ExprNode:
        left = self.parse_atom(tokens)

        while tokens.peek().type in (TokenType.PLUS, TokenType.MINUS):
            op = tokens.pop()
            right = self.parse_atom(tokens)

            left = BinOp(
                Span(left.span.begin, right.span.end),
                BinOpType.ADD if op.type is TokenType.PLUS else BinOpType.SUB,
                left,
                right,
            )

        return left

    def parse_atom(self, tokens: PushbackTokenStream) -> ExprNode:
        tok = tokens.pop()

        match tok.type:
            case TokenType.IDENT:
                return IdentifierNode(tok.span, tok.value)

            case TokenType.STRING:
                return StringNode(tok.span, tok.value)

            case TokenType.LPAREN:
                expr = self.parse_expr(tokens)

                closing = tokens.pop()

                if closing.type != TokenType.RPAREN:
                    raise UnexpectedToken(self.error_s, (TokenType.RPAREN,), closing)

                return expr

        raise UnexpectedToken(self.error_s, (TokenType.IDENT, TokenType.STRING, TokenType.LPAREN), tok)


def parse(tokens: t.Iterable[Token], max_depth: int, *, error_s: str) -> ExprNode:
    stream = PushbackTokenStream(tokens)

    result = _Parser(max_depth, error_s).parse_expr(stream)

    tok = stream.pop()

    if tok.type is not TokenType.NONE:
        raise UnexpectedToken(error_s, (TokenType.NONE,), tok)

    return result


def _try_consume_keyword(
    tokens: PushbackTokenStream,
    keyword: KeywordType,
) -> bool:
    tok = tokens.peek()

    if tok.type != TokenType.IDENT:
        return False

    if tok.value != keyword:
        return False

    tokens.pop()
    return True
