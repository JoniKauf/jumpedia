import typing as t
from dataclasses import dataclass

from jumpedia.interfaces.dsls.core.lex import Token, TokenType
from jumpedia.interfaces.dsls.core.parse import (
    BaseParser,
    ExprNode,
    IdentifierNode,
    PushbackTokenStream,
    TextNodeT,
)
from jumpedia.interfaces.dsls.core.value_objects import Span


@dataclass(frozen=True, slots=True)
class SequenceNode(ExprNode):
    elements: tuple[TextNodeT, ...]


class SequenceParser(BaseParser):
    def parse(self, tokens: t.Iterable[Token]) -> SequenceNode:
        stream = PushbackTokenStream(tokens)

        res: list[TextNodeT] = []

        while (next := stream.pop()).type is not TokenType.NONE:
            res.append(self.text_token_to_node(next))

        assert res

        if len(res) == 1:
            single = res[0]

            if isinstance(single, IdentifierNode) and single.name == "_":
                return SequenceNode(single.span, ())

        return SequenceNode(Span(res[0].span.begin, res[-1].span.end), tuple(res))
