from dataclasses import dataclass

from interfaces.dsls.core.errors.base import DslError
from interfaces.dsls.core.lex import Token, TokenType


@dataclass()
class ParseError(DslError):
    """Base class of all errors that occur in the parsing phase."""

    s: str


@dataclass()
class UnexpectedToken(ParseError):
    expected: tuple[TokenType, ...]
    received: Token


@dataclass()
class DepthLimitSurpassed(ParseError):
    at: Token
    max_depth: int
