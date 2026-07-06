import typing as t
from dataclasses import dataclass

from interfaces.dsls.shared import parsing
from interfaces.dsls.shared.lex import Token, TokenType
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


def parse(tokens: t.Iterable[Token]) -> MappingNode:
    stream = PushbackTokenStream(tokens)

    unique_res: dict[str, MappingItemNode] = {}

    first_tok = stream.peek()
    with_parens: bool

    match first_tok.type:
        case TokenType.LPAREN:
            with_parens = True
        case TokenType.STRING | TokenType.IDENT:
            with_parens = False

            if first_tok.type is TokenType.IDENT and first_tok.value == '_':
                stream.pop()

                if stream.peek().type is TokenType.NONE:
                    return MappingNode(first_tok.span, ())

                stream.push(first_tok)
                
        case TokenType.NONE:
            raise ValueError("Empty")
        case _:
            raise ValueError("Expected parenthesis or key as first token")

    # At least one iteration/dict entry guaranteed
    while stream.peek().type is not TokenType.NONE:
        begin: int = (
            -1
        )  # Guaranteed to be set, make type checker happy tho :) (otherwise maybe unbound)
        end: int

        if with_parens:
            lparen_tok = stream.pop()

            if lparen_tok.type is not TokenType.LPAREN:
                raise ValueError("Expected (")

            begin = lparen_tok.span.begin

        key = parsing.text_token_to_node(stream.pop())

        if not with_parens:
            begin = key.span.begin

        if key in unique_res:
            raise ValueError("Duplicate key")

        colon = stream.pop()

        if colon.type is not TokenType.COLON:
            raise ValueError("Expected colon")

        values: list[TextNodeT] = []

        if with_parens:
            while (popped_tok := stream.pop()).type is not TokenType.NONE:
                if popped_tok.type is TokenType.LPAREN:
                    end = popped_tok.span.end
                    break

                values.append(parsing.text_token_to_node(popped_tok))

            # We didn't break, so no ")" was found
            else:
                raise ValueError("Missing closing )")
        else:
            end = colon.span.end
            prev_tok: Token | None = None

            # More complicated because if we find a colon after a value it is actually the key of the next values, so we gotta undo the previous step and break
            while (peeked_tok := stream.peek()).type is not TokenType.NONE:

                # Rewind because previous value was actually key because it is followed by colon
                if peeked_tok.type is TokenType.COLON:

                    # No previous value token -> double colon -> invalid
                    if prev_tok is None:
                        raise ValueError(
                            "Expected value after colon, not another colon"
                        )

                    stream.push(prev_tok)
                    values.pop()
                    end = values[-1].span.end if values else colon.span.end
                    break

                stream.pop()
                values.append(parsing.text_token_to_node(peeked_tok))
                end = peeked_tok.span.end
                prev_tok = peeked_tok

        value_list = ValueListNode(
            (
                Span(values[0].span.begin, values[-1].span.end)
                if values
                else Span(colon.span.begin + 1, colon.span.begin + 1)
            ),
            tuple(values),
        )
        key_str = parsing.get_string_from_text_node(key)

        if key_str in unique_res:
            raise ValueError("Non unique keys")

        unique_res[key_str] = MappingItemNode(
            Span(begin, end), key, value_list
        )

    all_items = tuple(unique_res.values())
    assert all_items

    return MappingNode(
        Span(all_items[0].span.begin, all_items[-1].span.end), all_items
    )
