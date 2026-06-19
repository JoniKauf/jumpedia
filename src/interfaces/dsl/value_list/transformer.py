import typing as t
from dataclasses import dataclass

from interfaces.dsl.shared.lexer import NONE_TOKEN, Token, TokenType
from interfaces.dsl.shared.transformer import (
    ExprNode,
    IdentifierNode,
    PushbackTokenStream,
    StringNode,
    StringyNodeT,
    stringy_token_to_node,
)
from interfaces.dsl.shared.value_objects import Span


@dataclass(frozen=True, slots=True)
class ValueListNode(ExprNode):
    elements: tuple[StringyNodeT, ...]


class ValueListTransformer:
    def transform(self, tokens: t.Iterable[Token]) -> ValueListNode:
        stream = PushbackTokenStream(tokens)

        res: list[StringyNodeT] = []

        while (next := stream.pop()).type is not TokenType.NONE:
            res.append(stringy_token_to_node(next))

        if not res:
            raise ValueError("Empty")

        return ValueListNode(Span(res[0].span.begin, res[-1].span.end), tuple(res))
