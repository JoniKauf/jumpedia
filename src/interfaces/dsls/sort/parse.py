import typing as t
from dataclasses import dataclass

from interfaces.dsls.shared import parsing
from interfaces.dsls.shared.errors.parse import UnexpectedToken
from interfaces.dsls.shared.lexing import Token, TokenType
from interfaces.dsls.shared.parsing import ExprNode, PushbackTokenStream, TextNodeT
from interfaces.dsls.shared.value_objects import Span


@dataclass(frozen=True, slots=True)
class SortElementNode(ExprNode):
    value: TextNodeT
    asc: bool


@dataclass(frozen=True, slots=True)
class SortListNode(ExprNode):
    elements: tuple[SortElementNode, ...]


def parse(tokens: t.Iterable[Token], *, error_s: str) -> SortListNode:
    stream = PushbackTokenStream(tokens)

    res: list[SortElementNode] = []

    ASC_OPS: t.Final = (TokenType.PLUS, TokenType.MINUS)

    while (next := stream.pop()).type is not TokenType.NONE:
        asc_op = next

        if asc_op.type not in ASC_OPS:
            raise UnexpectedToken(error_s, ASC_OPS, asc_op)

        value = parsing.text_token_to_node(stream.pop(), error_s=error_s)
        
        res.append(
            SortElementNode(
                Span(value.span.begin, asc_op.span.end),
                value,
                asc_op.type is TokenType.PLUS,
            )
        )

    assert res

    return SortListNode(Span(res[0].span.begin, res[-1].span.end), tuple(res))
