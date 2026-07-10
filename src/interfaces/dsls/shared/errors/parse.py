from dataclasses import dataclass

from interfaces.dsls.shared.errors.base import DslError
from interfaces.dsls.shared.lexing import Token, TokenType


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