import typing as t
from dataclasses import dataclass

from interfaces.dsls.shared import parsing
from interfaces.dsls.shared.errors.parse import UnexpectedToken
from interfaces.dsls.shared.lexing import TEXT_TOKEN_TYPES, Token, TokenType
from interfaces.dsls.shared.parsing import ExprNode, PushbackTokenStream, TextNodeT
from interfaces.dsls.shared.value_objects import Span


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


def parse(tokens: t.Iterable[Token], *, error_s: str) -> MappingNode:
    stream = PushbackTokenStream(tokens)

    first_tok = stream.peek()
    with_parens: bool

    res: list[MappingItemNode] = []

    match first_tok.type:
        case TokenType.LPAREN:
            with_parens = True
        case text if text in TEXT_TOKEN_TYPES:
            with_parens = False
            
            if first_tok.type is TokenType.IDENT and first_tok.value == "_":
                stream.pop()

                if stream.peek().type is TokenType.NONE:
                    return MappingNode(first_tok.span, ())

                stream.push(first_tok)

        case TokenType.NONE:
            assert False
        case _:
            raise UnexpectedToken(error_s, TEXT_TOKEN_TYPES + (TokenType.LPAREN,), first_tok)

    # At least one iteration guaranteed
    while stream.peek().type is not TokenType.NONE:
        # Mark not unbound for type checker
        item_begin: int = -1
        item_end: int

        if with_parens:
            lparen_tok = stream.pop()

            if lparen_tok.type is not TokenType.LPAREN:
                raise UnexpectedToken(error_s, (TokenType.LPAREN,), lparen_tok)

            item_begin = lparen_tok.span.begin

        key_token = stream.pop()
        key_node = parsing.text_token_to_node(key_token, error_s=error_s)

        if not with_parens:
            item_begin = key_node.span.begin

        colon = stream.pop()

        if colon.type is not TokenType.COLON:
            raise UnexpectedToken(error_s, (TokenType.COLON,), colon)

        values: list[TextNodeT] = []

        if with_parens:
            while (popped_tok := stream.pop()).type is not TokenType.NONE:
                if popped_tok.type is TokenType.LPAREN:
                    item_end = popped_tok.span.end
                    break

                values.append(parsing.text_token_to_node(popped_tok, error_s=error_s))

            # We didn't break, so no ")" was found
            else:
                raise UnexpectedToken(error_s, (TokenType.RPAREN,), popped_tok)
        else:
            while (tok := stream.pop()).type is not TokenType.NONE:
                if stream.peek().type is TokenType.COLON:
                    # We are after "key:" so if we receive another colon, bad
                    if not values:
                        raise UnexpectedToken(error_s, TEXT_TOKEN_TYPES, stream.pop())

                    # Otherwise if we see the next token is a colon, "tok" is the key of the next item
                    # Undo adding to to the current values and stop for this item
                    stream.push(tok)
                    values.pop()
                    break

                values.append(parsing.text_token_to_node(tok, error_s=error_s))
            
            item_end = values[-1].span.end if values else colon.span.end

        value_list = ValueListNode(
            (
                Span(values[0].span.begin, values[-1].span.end)
                if values
                else Span(colon.span.begin + 1, colon.span.begin + 1)
            ),
            tuple(values),
        )

        res.append(MappingItemNode(Span(item_begin, item_end), key_node, value_list))

    assert res

    return MappingNode(Span(res[0].span.begin, res[-1].span.end), tuple(res))
