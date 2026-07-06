import typing as t
from dataclasses import dataclass

from interfaces.dsls.shared import parsing
from interfaces.dsls.shared.lex import Token, TokenType
from interfaces.dsls.shared.parsing import ExprNode, PushbackTokenStream, TextNodeT
from interfaces.dsls.shared.value_objects import Span


@dataclass(frozen=True, slots=True)
class ValueListNode(ExprNode):
    elements: tuple[TextNodeT, ...]


def parse(tokens: t.Iterable[Token]) -> ValueListNode:
    stream = PushbackTokenStream(tokens)

    res: list[TextNodeT] = []

    while (next := stream.pop()).type is not TokenType.NONE:
        res.append(parsing.text_token_to_node(next))

    if not res:
        raise ValueError("Empty")

    return ValueListNode(Span(res[0].span.begin, res[-1].span.end), tuple(res))
