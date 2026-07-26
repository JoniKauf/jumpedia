from dataclasses import dataclass

from interfaces.dsls.core.errors.base import DslError
from interfaces.dsls.core.value_objects import Span


@dataclass()
class LexError(DslError):
    """Base class of all errors that occur in the lexing phase."""

    s: str
    span: Span


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
