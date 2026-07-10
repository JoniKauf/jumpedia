import functools
import typing as t
from dataclasses import dataclass

from interfaces.dsls.shared import lexing
from interfaces.dsls.shared.errors.parse import UnexpectedToken
from interfaces.dsls.shared.value_objects import Span


class PushbackTokenStream:
    def __init__(self, iterable: t.Iterable[lexing.Token]):
        self._it = iter(iterable)
        self._buf: list[lexing.Token] = []

    def pop(self) -> lexing.Token:
        if self._buf:
            return self._buf.pop()
        return next(self._it, lexing.NONE_TOKEN)

    def push(self, tok: lexing.Token) -> None:
        self._buf.append(tok)

    def peek(self) -> lexing.Token:
        if self._buf:
            return self._buf[-1]
        tok = next(self._it, None)
        if tok is None:
            return lexing.NONE_TOKEN
        self._buf.append(tok)
        return tok


@dataclass(frozen=True, slots=True)
class ExprNode:
    span: Span


@dataclass(frozen=True, slots=True)
class IdentifierNode(ExprNode):
    name: str


@dataclass(frozen=True, slots=True)
class StringNode(ExprNode):
    value: str


type TextNodeT = StringNode | IdentifierNode

def text_token_to_node(tok: lexing.Token, *, error_s: str) -> TextNodeT:
    if tok.type is lexing.TokenType.IDENT:
        return IdentifierNode(tok.span, tok.value)

    if tok.type is lexing.TokenType.STRING:
        return StringNode(tok.span, tok.value)

    raise UnexpectedToken(error_s, (lexing.TokenType.IDENT, lexing.TokenType.STRING), tok)
