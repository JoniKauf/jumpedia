import typing as t
from dataclasses import dataclass

from jumpedia.interfaces.dsls.core.errors.parse import UnexpectedToken
from jumpedia.interfaces.dsls.core.lex import TEXT_TOKEN_TYPES, Token, TokenType
from jumpedia.interfaces.dsls.core.parse import (
    BaseParser,
    ExprNode,
    IdentifierNode,
    PushbackTokenStream,
    StringNode,
    TextNodeT,
)
from jumpedia.interfaces.dsls.core.value_objects import Span


@dataclass(frozen=True, slots=True)
class ValueListNode(ExprNode):
    elements: tuple[TextNodeT, ...]


@dataclass(frozen=True, slots=True)
class MappingItemNode(ExprNode):
    key: TextNodeT
    value: ValueListNode


@dataclass(frozen=True, slots=True)
class MappingNode(ExprNode):
    items: tuple[MappingItemNode, ...]


def _create_mapping_item_node_no_parentheses(
    key: TextNodeT, colon: Token, values: t.Sequence[TextNodeT]
) -> MappingItemNode:
    return MappingItemNode(
        Span(
            key.span.begin,
            values[-1].span.end if values else colon.span.end,
        ),
        key,
        ValueListNode(
            (
                Span(values[0].span.begin, values[-1].span.end)
                if values
                else Span(colon.span.end, colon.span.end)
            ),
            tuple(values),
        ),
    )


class MappingParser(BaseParser):
    def _parse_with_parentheses(self, stream: PushbackTokenStream) -> MappingNode:
        items: list[MappingItemNode] = []

        while stream.peek().type is not TokenType.NONE:
            lparen = self.expect(stream.pop(), TokenType.LPAREN)

            key = self.text_token_to_node(self.expect(stream.pop(), *TEXT_TOKEN_TYPES))

            colon = self.expect(stream.pop(), TokenType.COLON)

            values: list[TextNodeT] = []

            while stream.peek().type in TEXT_TOKEN_TYPES:
                values.append(self.text_token_to_node(stream.pop()))

            rparen = self.expect(stream.pop(), TokenType.RPAREN)

            item = MappingItemNode(
                Span(lparen.span.begin, rparen.span.end),
                key,
                ValueListNode(
                    (
                        Span(values[0].span.begin, values[-1].span.end)
                        if values
                        else Span(colon.span.end, colon.span.end)
                    ),
                    tuple(values),
                ),
            )

            items.append(item)

        assert items

        return MappingNode(Span(items[0].span.begin, items[-1].span.end), tuple(items))

    def _parse_without_parentheses(self, stream: PushbackTokenStream) -> MappingNode:
        items: list[MappingItemNode] = []

        while True:
            key = self.text_token_to_node(self.expect(stream.pop(), *TEXT_TOKEN_TYPES))

            colon = self.expect(stream.pop(), TokenType.COLON)

            values: list[TextNodeT] = []

            while stream.peek().type in TEXT_TOKEN_TYPES:
                values.append(self.text_token_to_node(stream.pop()))

            # Only peek!
            colon_or_end = self.expect(stream.peek(), TokenType.COLON, TokenType.NONE)

            if colon_or_end.type is TokenType.NONE:
                # Add last item
                items.append(
                    _create_mapping_item_node_no_parentheses(key, colon, values)
                )
                break

            # It is a colon so the last elem we added is in reality the key of the next
            # item. Undo those steps.

            # If we have 2 colons in a row, for exampe "value: :" then that is wrong.
            if not values:
                raise UnexpectedToken(
                    self._s, (TokenType.NONE, *TEXT_TOKEN_TYPES), colon_or_end
                )

            # Pop from list of values
            key_of_next_item_as_node = values.pop()
            key_of_next_item: Token

            match key_of_next_item_as_node:
                case IdentifierNode() as ident_node:
                    key_of_next_item = Token(
                        TokenType.IDENT, ident_node.span, ident_node.name
                    )

                case StringNode() as string_node:
                    key_of_next_item = Token(
                        TokenType.STRING, string_node.span, string_node.value
                    )

                case _:
                    t.assert_never(key_of_next_item_as_node)

            # Push back onto stream for next key, values pair
            stream.push(key_of_next_item)

            items.append(_create_mapping_item_node_no_parentheses(key, colon, values))

        assert items

        return MappingNode(Span(items[0].span.begin, items[-1].span.end), tuple(items))

    def parse(self, tokens: t.Iterable[Token]) -> MappingNode:
        stream = PushbackTokenStream(tokens)

        first_tok = stream.peek()

        if first_tok.type is TokenType.IDENT and first_tok.value == "_":
            stream.pop()

            if stream.peek().type is TokenType.NONE:
                return MappingNode(first_tok.span, ())

            stream.push(first_tok)

        if first_tok.type is TokenType.LPAREN:
            return self._parse_with_parentheses(stream)

        return self._parse_without_parentheses(stream)
