import typing as t
from dataclasses import dataclass

from interfaces.dsl.shared.lexer import Token
from interfaces.dsl.shared.value_objects import Span


class PushbackTokenStream:
    def __init__(self, iterable: t.Iterable[Token]):
        self._it = iter(iterable)
        self._buf: list[Token] = []

    def pop(self) -> Token | None:
        if self._buf:
            return self._buf.pop()
        return next(self._it, None)

    def push(self, tok: Token) -> None:
        self._buf.append(tok)

    def peek(self) -> Token | None:
        if self._buf:
            return self._buf[-1]
        tok = next(self._it, None)
        if tok is None:
            return None
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
