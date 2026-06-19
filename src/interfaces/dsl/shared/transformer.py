import typing as t
from dataclasses import dataclass

from interfaces.dsl.shared.lexer import NONE_TOKEN, Token, TokenType
from interfaces.dsl.shared.value_objects import Span


class PushbackTokenStream:
    def __init__(self, iterable: t.Iterable[Token]):
        self._it = iter(iterable)
        self._buf: list[Token] = []

    def pop(self) -> Token:
        if self._buf:
            return self._buf.pop()
        return next(self._it, NONE_TOKEN)

    def push(self, tok: Token) -> None:
        self._buf.append(tok)

    def peek(self) -> Token:
        if self._buf:
            return self._buf[-1]
        tok = next(self._it, None)
        if tok is None:
            return NONE_TOKEN
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


type StringyNodeT = StringNode | IdentifierNode


def get_string_from_stringy_node(node: StringyNodeT) -> str:
    if isinstance(node, StringNode):
        return node.value

    return node.name


def stringy_token_to_node(tok: Token) -> StringyNodeT:
    if tok.type is TokenType.IDENT:
        return IdentifierNode(tok.span, tok.value)

    if tok.type is TokenType.STRING:
        return StringNode(tok.span, tok.value)

    raise ValueError("Unexpected token")
