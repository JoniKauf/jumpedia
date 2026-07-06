from token import MINUS
import typing as t
from dataclasses import dataclass

from interfaces.dsls.shared import parsing
from interfaces.dsls.shared.lex import Token, TokenType
from interfaces.dsls.shared.parsing import ExprNode, PushbackTokenStream, TextNodeT
from interfaces.dsls.shared.value_objects import Span


@dataclass(frozen=True, slots=True)
class SortElementNode(ExprNode):
    value: TextNodeT
    asc: bool


@dataclass(frozen=True, slots=True)
class SortListNode(ExprNode):
    elements: tuple[SortElementNode, ...]


def parse(tokens: t.Iterable[Token]) -> SortListNode:
    stream = PushbackTokenStream(tokens)

    res: list[SortElementNode] = []

    while (next := stream.pop()).type is not TokenType.NONE:
        value = parsing.text_token_to_node(next)
        asc_op = stream.pop()

        if asc_op.type not in (TokenType.PLUS, TokenType.MINUS):
            raise ValueError("Not an operator")

        res.append(
            SortElementNode(
                Span(value.span.begin, asc_op.span.end),
                value,
                asc_op.type is TokenType.PLUS,
            )
        )

    if not res:
        raise ValueError("Empty")

    return SortListNode(Span(res[0].span.begin, res[-1].span.end), tuple(res))
