
import enum
import typing as t
from dataclasses import dataclass

from interfaces.dsl.shared.lex import Token, TokenType
from interfaces.dsl.shared.parsing import (ExprNode, IdentifierNode,
                                           PushbackTokenStream, StringNode,
                                           TextNodeT)
from interfaces.dsl.shared.value_objects import Span


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

class KeywordType(enum.Enum):
    

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

def parse(tokens: t.Iterable[Token], max_depth: int) -> ExprNode:
    stream = PushbackTokenStream(tokens)

    result = _Parser(max_depth).parse_expr(stream)

    tok = stream.pop()

    if tok.type is not TokenType.NONE:
        raise ParseError(f"Unexpected token {tok}")

    return result

def _try_consume_keyword(
    tokens: PushbackTokenStream,
    keyword: str,
) -> IdentifierNode:
    tok = tokens.peek()

    if tok.type != TokenType.IDENT:
        return False

    if tok.value != keyword:
        return False

    tokens.pop()
    return True


class _Parser:
    def __init__(self, max_depth: int) -> None:
        self.max_depth = max_depth
        self.depth = 0

    def parse_expr(self, tokens: PushbackTokenStream) -> ExprNode:
        self.depth += 1

        try:
            if self.depth > self.max_depth:
                raise ParseError
            
            return self.parse_or(tokens)
        finally:
            self.depth -= 1

    def parse_conditional(self, tokens: PushbackTokenStream) -> ExprNode:
        true_value = self.parse_or(tokens)

        tok = tokens.peek()

        if (
            tok.type == TokenType.IDENT
            and tok.value == "if"
        ):
            tokens.pop()

            condition = self.parse_or(tokens)

            else_tok = tokens.pop()

            if (
                else_tok.type != TokenType.IDENT
                or else_tok.value != "else"
            ):
                raise ParseError("Expected 'else'")

            false_value = self.parse_conditional(tokens)

            return ConditionalExpr(
                Span(true_value.span.begin, false_value.span.end),
                condition,
                true_value,
                false_value,
            )

        return true_value

    def parse_or(self, tokens: PushbackTokenStream) -> ExprNode:
        elements: list[ExprNode] = [self.parse_and(tokens)]

        while _try_consume_keyword(tokens, "or"):
            elements.append(self.parse_and(tokens))

        if len(elements) == 1:
            return elements[0]

        assert len(elements) > 1

        return BoolOp(Span(elements[0].span.begin, elements[-1].span.end), BoolOpType.OR, tuple(elements))


    def parse_and(self, tokens: PushbackTokenStream) -> ExprNode:
        elements: list[ExprNode] = [self.parse_comparison(tokens)]

        while _try_consume_keyword(tokens, "and"):
            elements.append(self.parse_comparison(tokens))

        if len(elements) == 1:
            return elements[0]

        assert len(elements) > 1

        return BoolOp(Span(elements[0].span.begin, elements[-1].span.end), BoolOpType.AND, tuple(elements))


    def parse_comparison(self, tokens: PushbackTokenStream) -> ExprNode:
        left = self.parse_additive(tokens)

        if _try_consume_keyword(tokens, "is"):
            op_type = BinOpType.IS_NOT if _try_consume_keyword(tokens, "not") else BinOpType.IS

            right = self.parse_atom(tokens)

            return BinOp(
                Span(left.span.begin, right.span.end),
                op_type,
                left,
                right,
            )

        tok = tokens.peek()

        for tok_type, bin_op_type in ((TokenType.LT, BinOpType.LT),( TokenType.LTE, BinOpType.LTE), (TokenType.GT, BinOpType.GT), (TokenType.GTE, BinOpType.GTE)):
            if tok.type != tok_type:
                continue
            
            tokens.pop()
            right = self.parse_atom(tokens)

            return BinOp(
                Span(left.span.begin, right.span.end),
                bin_op_type,
                left,
                right,
            )

        return left
    
    def parse_additive(self, tokens: PushbackTokenStream) -> ExprNode:
        left = self.parse_atom(tokens)

        while tokens.peek().type == TokenType.PLUS:
            op = tokens.pop()
            right = self.parse_atom(tokens)

            left = BinOp(
                Span(left.span.begin, right.span.end),
                BinOpType.ADD,
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
                    raise ParseError("Expected ')'")

                return expr

        raise ParseError(f"Unexpected token {tok}")