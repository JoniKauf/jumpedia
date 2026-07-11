from dataclasses import dataclass

from interfaces.dsls.core.errors.base import DslError
from interfaces.dsls.core.value_objects import Span


@dataclass(frozen=True, slots=True)
class LexError(DslError):
    """Base class of all errors that occur in the lexing phase."""

    s: str
    span: Span


@dataclass(frozen=True, slots=True)
class InvalidEscape(LexError):
    pass


@dataclass(frozen=True, slots=True)
class MultilineStringsDisallowed(LexError):
    pass


@dataclass(frozen=True, slots=True)
class UnterminatedString(LexError):
    unterminated_escape: bool


@dataclass(frozen=True, slots=True)
class UnknownChar(LexError):
    pass
