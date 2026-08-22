import enum
import types as ts
import typing as t
from dataclasses import dataclass

from jumpedia.interfaces.dsls.core.errors.lex import (
    InvalidEscape,
    MultilineStringsDisallowed,
    UnknownChar,
    UnterminatedString,
)
from jumpedia.interfaces.dsls.core.value_objects import Span


class TokenType(enum.Enum):
    # Used for when there are no more tokens left
    # Working with "TokenType | None" is awful, this is way nicer
    NONE = enum.auto()

    # Text
    STRING = enum.auto()
    IDENT = enum.auto()

    # Parentheses
    LPAREN = enum.auto()
    RPAREN = enum.auto()

    # Comparison Ops
    LT = enum.auto()
    LTE = enum.auto()
    GT = enum.auto()
    GTE = enum.auto()

    # Addition
    PLUS = enum.auto()
    MINUS = enum.auto()

    # Delimiters
    COLON = enum.auto()
    COMMA = enum.auto()

    # Keywords
    IF = enum.auto()
    ELSE = enum.auto()
    IS = enum.auto()
    CONTAINS = enum.auto()
    NOT = enum.auto()
    OR = enum.auto()
    AND = enum.auto()


# Invariant: NO SYMBOL AND IDENTIFIER CHARS MAY OVERLAP!!
SYMBOLS: t.Final[frozendict[str, TokenType]] = frozendict(
    {
        "(": TokenType.LPAREN,
        ")": TokenType.RPAREN,
        ":": TokenType.COLON,
        ",": TokenType.COMMA,
        "+": TokenType.PLUS,
        "-": TokenType.MINUS,
        "<": TokenType.LT,
        "<=": TokenType.LTE,
        ">": TokenType.GT,
        ">=": TokenType.GTE,
    }
)

KEYWORDS: t.Final[frozendict[str, TokenType]] = frozendict(
    {
        "if": TokenType.IF,
        "else": TokenType.ELSE,
        "is": TokenType.IS,
        "contains": TokenType.CONTAINS,
        "not": TokenType.NOT,
        "or": TokenType.OR,
        "and": TokenType.AND,
    }
)


@dataclass(frozen=True, slots=True)
class Token:
    type: TokenType
    span: Span
    value: str


TEXT_TOKEN_TYPES: t.Final = (TokenType.IDENT, TokenType.STRING)

NONE_TOKEN: t.Final = Token(TokenType.NONE, Span(-1, -1), "")
QUOTES: t.Final[frozenset[str]] = frozenset("'" + '"')
ESCAPES: t.Final[frozendict[str, str]] = frozendict(
    {"\\": "\\", '"': '"', "'": "'", "n": "\n"}
)


@t.final
class Lexer:
    def __init__(self, *, multiline_strings: bool) -> None:
        self._multiline_strings = multiline_strings

    def lex(self, s: str) -> t.Generator[Token]:
        SYMBOLS_LONGEST_TO_SHORTEST: t.Final[tuple[str, ...]] = tuple(
            sorted(SYMBOLS, key=len, reverse=True)
        )

        i: int = 0
        length = len(s)

        while i < length:
            c = s[i]

            if c.isspace():
                i += 1
                continue

            # --- Lex String --- #
            if c in QUOTES:
                buf: list[str] = []
                j: int = i + 1
                escaped: bool = False

                while j < length:
                    cc = s[j]

                    if escaped:
                        escaped_v = ESCAPES.get(cc)

                        if escaped_v is None:
                            raise InvalidEscape(s, Span(j - 1, j + 1))

                        if not self._multiline_strings and escaped_v == "\n":
                            raise MultilineStringsDisallowed(s, Span(j - 1, j + 1))

                        buf.append(escaped_v)
                        escaped = False

                    elif cc == "\\":
                        escaped = True

                    elif cc == c:
                        break

                    else:
                        buf.append(cc)

                    j += 1
                else:
                    raise UnterminatedString(s, Span(i, j), escaped)

                j += 1  # Skip closing quote
                yield Token(TokenType.STRING, Span(i, j), "".join(buf))

                i = j
                continue

            # --- Lex Keyword OR Identifier --- #
            if self.is_identifier_char(c):
                j: int = i + 1

                while j < length:
                    cc = s[j]

                    if not self.is_identifier_char(cc):
                        break

                    j += 1

                value = s[i:j]
                span = Span(i, j)

                kw = KEYWORDS.get(value)

                if kw is not None:
                    yield Token(kw, span, value)
                else:
                    yield Token(TokenType.IDENT, span, value)

                i = j
                continue

            # --- Lex Symbol --- #
            for symbol in SYMBOLS_LONGEST_TO_SHORTEST:
                if s.startswith(symbol, i):
                    break
            else:
                # End point of lexing, nothing matched
                raise UnknownChar(s, Span(i, i + 1))

            j = i + len(symbol)
            yield Token(SYMBOLS[symbol], Span(i, j), symbol)

            i = j

    def is_identifier_char(self, c: str) -> bool:
        return c == "_" or c.isalnum()
