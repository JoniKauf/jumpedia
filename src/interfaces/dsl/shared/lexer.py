import enum
import types as ts
import typing as t
from dataclasses import dataclass

from interfaces.dsl.shared.value_objects import Span


class TokenType(enum.Enum):
    NONE = 0
    STRING = 1
    IDENT = 2
    LPAREN = 3
    RPAREN = 4
    PLUS = 5
    LT = 6
    LE = 7
    GT = 8
    GE = 9
    COLON = 10
    COMMA = 11


SYMBOLS: dict[str, TokenType] = {
    "(": TokenType.LPAREN,
    ")": TokenType.RPAREN,
    ":": TokenType.COLON,
    ",": TokenType.COMMA,
    "+": TokenType.PLUS,
    "<": TokenType.LT,
    "<=": TokenType.LE,
    ">": TokenType.GT,
    ">=": TokenType.GE,
}


@dataclass(frozen=True, slots=True)
class Token:
    type: TokenType
    span: Span
    value: str


NONE_TOKEN = Token(TokenType.NONE, Span(-1, -1), "")


@t.final
class Lexer:
    def __init__(self, *, multiline: bool) -> None:
        self.multiline: t.Final[bool] = multiline

    QUOTES: t.ClassVar[frozenset[str]] = frozenset("'" + '"')
    ESCAPES: t.ClassVar[ts.MappingProxyType[str, str]] = ts.MappingProxyType(
        {"\\": "\\", '"': '"', "'": "'", "n": "\n"}
    )

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
            if c in self.QUOTES:
                buf: list[str] = []
                j: int = i + 1
                escaped: bool = False

                while j < length:
                    cc = s[j]

                    if escaped:
                        escaped_v = self.ESCAPES.get(cc)

                        if escaped_v is None:
                            raise ValueError(f"Unescapable char '{cc}'")

                        if not self.multiline and escaped_v == "\n":
                            raise ValueError("Single line mode")

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
                    if escaped:
                        raise ValueError("End reached in escape sequence in string")
                    else:
                        raise ValueError("End reached in string")

                j += 1  # Skip closing quote
                yield Token(TokenType.STRING, Span(i, j), "".join(buf))

                i = j
                continue

            # Invariant: No symbol and identifier chars overlap

            # --- Lex Identifier --- #
            if self.is_identifier_char(c):
                j: int = i + 1

                while j < length:
                    cc = s[j]

                    if not self.is_identifier_char(cc):
                        break

                    j += 1

                yield Token(TokenType.IDENT, Span(i, j), s[i:j])

                i = j
                continue

            # --- Lex Symbol --- #
            symbol: str | None = None

            for s in SYMBOLS_LONGEST_TO_SHORTEST:
                if s.startswith(s, i):
                    symbol = s
                    break

            # End point of lexing, nothing matched
            if symbol is None:
                raise ValueError(f"Invalid character '{s[i]}'")

            j = i + len(symbol)
            yield Token(SYMBOLS[symbol], Span(i, j), symbol)

            i = j

    def is_identifier_char(self, c: str) -> bool:
        return c == "_" or c.isalnum()
