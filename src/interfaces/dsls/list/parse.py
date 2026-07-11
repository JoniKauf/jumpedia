import typing as t
from dataclasses import dataclass

from interfaces.dsls.shared.lex import Token, TokenType
from interfaces.dsls.shared.parse import (
    BaseParser,
    ExprNode,
    IdentifierNode,
    PushbackTokenStream,
    TextNodeT,
)
from interfaces.dsls.shared.value_objects import Span


@dataclass(frozen=True, slots=True)
class ValueListNode(ExprNode):
    elements: tuple[TextNodeT, ...]


class ListParser(BaseParser):
    def parse(self, tokens: t.Iterable[Token]) -> ValueListNode:
        stream = PushbackTokenStream(tokens)

        res: list[TextNodeT] = []

        while (next := stream.pop()).type is not TokenType.NONE:
            res.append(self.text_token_to_node(next))

        assert res

        if len(res) == 1:
            single = res[0]

            if isinstance(single, IdentifierNode) and single.name == "_":
                return ValueListNode(single.span, ())

        return ValueListNode(Span(res[0].span.begin, res[-1].span.end), tuple(res))
