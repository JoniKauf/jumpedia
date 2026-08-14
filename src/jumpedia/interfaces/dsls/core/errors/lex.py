from dataclasses import dataclass

from jumpedia.interfaces.dsls.core.errors.base import DslError
from jumpedia.interfaces.dsls.core.value_objects import Span

type AnyLexErrorT = InvalidEscape | MultilineStringsDisallowed | UnterminatedString | UnknownChar


@dataclass()
class LexError(DslError):
    """Base class of all errors that occur in the lexing phase."""

    s: str
    span: Span

    @property
    def substring(self) -> str:
        return self.s[self.span.begin : self.span.end]


@dataclass()
class InvalidEscape(LexError):
    pass


@dataclass()
class MultilineStringsDisallowed(LexError):
    pass


@dataclass()
class UnterminatedString(LexError):
    unterminated_escape: bool


@dataclass()
class UnknownChar(LexError):
    pass
