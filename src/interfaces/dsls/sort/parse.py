import typing as t
from dataclasses import dataclass

from interfaces.dsls.core.errors.parse import UnexpectedToken
from interfaces.dsls.core.lex import Token, TokenType
from interfaces.dsls.core.parse import BaseParser, ExprNode, PushbackTokenStream, TextNodeT
from interfaces.dsls.core.value_objects import Span


@dataclass(frozen=True, slots=True)
class SortElementNode(ExprNode):
    value: TextNodeT
    asc: bool


@dataclass(frozen=True, slots=True)
class SortListNode(ExprNode):
    elements: tuple[SortElementNode, ...]


class SortParser(BaseParser):
    def parse(self, tokens: t.Iterable[Token]) -> SortListNode:
        stream = PushbackTokenStream(tokens)

        res: list[SortElementNode] = []

        ASC_OPS: t.Final = (TokenType.PLUS, TokenType.MINUS)

        while (next := stream.pop()).type is not TokenType.NONE:
            asc_op = next

            if asc_op.type not in ASC_OPS:
                raise UnexpectedToken(self._s, ASC_OPS, asc_op)

            value = self.text_token_to_node(stream.pop())
            
            res.append(
                SortElementNode(
                    Span(value.span.begin, asc_op.span.end),
                    value,
                    asc_op.type is TokenType.PLUS,
                )
            )

        assert res

        return SortListNode(Span(res[0].span.begin, res[-1].span.end), tuple(res))
