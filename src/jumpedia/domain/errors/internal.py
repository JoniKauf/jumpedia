"""Internal errors that are mostly used for assertions.

These DON'T need to be handled gracefully."""

from dataclasses import dataclass

lazy from jumpedia.domain.entities.base import BaseEntity
lazy from jumpedia.domain.enums.attribute import AttributeKind, AttributeType
lazy from jumpedia.domain.typing.attribute import AttributeID
lazy from jumpedia.domain.typing.common import ID


@dataclass()
class InternalError(Exception):
    pass


@dataclass()
class NotFoundById(InternalError):
    type: type[BaseEntity]
    id: ID


@dataclass()
class IntOutOfRange(InternalError):
    n: int
    range: tuple[int, int] | tuple[int, None] | tuple[None, int]


@dataclass()
class ProgrammingError(InternalError):
    msg: str


@dataclass()
class KindedAttributeMissing(InternalError):
    kind: AttributeKind


@dataclass()
class AttributeTypeKindMismatch(InternalError):
    id: AttributeID
    type: AttributeType
    kind: AttributeKind


@dataclass()
class UndefinedTypeForKind(InternalError):
    attribute: AttributeKind


@dataclass()
class InitialSlotCountMustBeZero(InternalError):
    pass
