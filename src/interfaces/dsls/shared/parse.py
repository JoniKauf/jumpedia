import functools
import typing as t
from dataclasses import dataclass

from interfaces.dsls.shared import lex
from interfaces.dsls.shared.errors.parse import UnexpectedToken
from interfaces.dsls.shared.value_objects import Span


class PushbackTokenStream:
    def __init__(self, iterable: t.Iterable[lex.Token]):
        self._it = iter(iterable)
        self._buf: list[lex.Token] = []

    def pop(self) -> lex.Token:
        if self._buf:
            return self._buf.pop()
        return next(self._it, lex.NONE_TOKEN)

    def push(self, tok: lex.Token) -> None:
        self._buf.append(tok)

    def peek(self) -> lex.Token:
        if self._buf:
            return self._buf[-1]
        tok = next(self._it, None)
        if tok is None:
            return lex.NONE_TOKEN
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


TextNodeT = IdentifierNode | StringNode

TEXT_NODE_TYPES = (IdentifierNode, StringNode)

class BaseParser:
    def __init__(self, s: str) -> None:
        self._s = s

    def text_token_to_node(self, tok: lex.Token) -> TextNodeT:
        if tok.type is lex.TokenType.IDENT:
            return IdentifierNode(tok.span, tok.value)

        if tok.type is lex.TokenType.STRING:
            return StringNode(tok.span, tok.value)

        raise UnexpectedToken(self._s, (lex.TokenType.IDENT, lex.TokenType.STRING), tok)
