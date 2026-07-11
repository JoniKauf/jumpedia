from dataclasses import dataclass

from interfaces.dsls.core.errors.base import DslError
from interfaces.dsls.core.lex import Token, TokenType


@dataclass(frozen=True, slots=True)
class ParseError(DslError):
    """Base class of all errors that occur in the parsing phase."""

    s: str


@dataclass(frozen=True, slots=True)
class UnexpectedToken(ParseError):
    expected: tuple[TokenType, ...]
    received: Token

@dataclass(frozen=True, slots=True)
class ExpectedKeyword(ParseError):
    expected: tuple[str, ...]
    received: Token

@dataclass(frozen=True, slots=True)
class DepthLimitSurpassed(ParseError):
    at: Token
    max_depth: int