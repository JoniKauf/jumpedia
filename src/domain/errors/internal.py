"""Internal errors that are mostly used for assertions.

These should not be handled gracefully."""


from dataclasses import dataclass

from domain.entities.base import BaseEntity

@dataclass()
class InternalError(Exception):
    pass


@dataclass()
class NotFoundById(InternalError):
    type: type[BaseEntity]


@dataclass()
class IntOutOfRange(InternalError):
    n: int
    range: tuple[int, int] | tuple[int, None] | tuple[None, int]


@dataclass()
class ProgrammingError(InternalError):
    msg: str