import typing as t
from dataclasses import dataclass

from interfaces.dsl.shared.lexer import IdentifierToken, StringToken, Token
from interfaces.dsl.shared.transformer import (ExprNode, IdentifierNode,
                                               PushbackTokenStream, StringNode)
from interfaces.dsl.shared.value_objects import Span


@dataclass(frozen=True, slots=True)
class ListNode(ExprNode):
    elements: tuple[IdentifierNode | StringNode, ...]


class Transformer:
    def transform(self, tokens: t.Iterable[Token]) -> ListNode:
        stream = PushbackTokenStream(tokens)

        res: list[StringNode | IdentifierNode] = []

        while (next := stream.pop()) is not None:
            if isinstance(next, IdentifierToken):
                res.append(IdentifierNode(next.span, next.value))
            elif isinstance(next, StringToken):
                res.append(StringNode(next.span, next.value))
            else:
                raise ValueError("Unexpected token")

        if not res:
            raise ValueError("Empty Collection")

        return ListNode(Span(res[0].span.begin, res[-1].span.end), tuple(res))
