import enum
import types as ts
import typing as t
from dataclasses import dataclass

from interfaces.dsl.shared.value_objects import Span


@dataclass(frozen=True, slots=True)
class Token:
    span: Span


@dataclass(frozen=True, slots=True)
class IdentifierToken(Token):
    value: str


@dataclass(frozen=True, slots=True)
class StringToken(Token):
    value: str


class SymbolKind(enum.StrEnum):
    LPAREN = "("
    RPAREN = ")"
    PLUS = "+"
    LT = "<"
    LE = "<="
    GT = ">"
    GE = ">="
    COMMA = ","


@dataclass(frozen=True, slots=True)
class SymbolToken(Token):
    value: SymbolKind


@t.final
class Lexer:
    def __init__(self, *, multiline: bool) -> None:
        self.multiline: t.Final[bool] = multiline

    QUOTES: t.ClassVar[frozenset[str]] = frozenset("'" + '"')
    ESCAPES: t.ClassVar[ts.MappingProxyType[str, str]] = ts.MappingProxyType(
        {"\\": "\\", '"': '"', "'": "'", "n": "\n"}
    )

    def lex(self, s: str) -> t.Generator[Token]:
        SYMBOL_KINDS_LONGEST_TO_SHORTEST: t.Final[tuple[SymbolKind, ...]] = tuple(
            sorted(SymbolKind, key=len, reverse=True)
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
                yield StringToken(Span(i, j), "".join(buf))

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

                yield IdentifierToken(Span(i, j), s[i:j])

                i = j
                continue

            # --- Lex Symbol --- #
            kind: SymbolKind | None = None

            for k in SYMBOL_KINDS_LONGEST_TO_SHORTEST:
                if s.startswith(k, i):
                    kind = k
                    break

            if kind is None:
                raise ValueError(f"unknown symbol '{s[i]}'")

            j = i + len(kind)
            yield SymbolToken(Span(i, j), kind)

            i = j

    def is_identifier_char(self, c: str) -> bool:
        return c == "_" or c.isalnum()
