import decimal
import enum
import typing as t

from domain.types.attribute import (
    AnyAttributeTypeT,
    SlotTypeT,
    TaskAttributeTypeT,
    UserAttributeTypeT,
)


@enum.verify(enum.UNIQUE, enum.CONTINUOUS)
class AttributeType(enum.IntEnum):
    TASK = 1
    USER = 2

    @t.overload
    def as_set(self: TaskAttributeTypeT) -> t.AbstractSet[TaskAttributeTypeT]:
        pass

    @t.overload
    def as_set(self: UserAttributeTypeT) -> t.AbstractSet[UserAttributeTypeT]:
        pass

    def as_set(  # pyright: ignore[reportInconsistentOverload]
        self,
    ) -> t.AbstractSet[t.Self]:
        return {self}

    @classmethod
    def ALL(cls) -> t.AbstractSet[AnyAttributeTypeT]:
        return {cls.TASK, cls.USER}

@enum.verify(enum.UNIQUE)
class AttributeKind(enum.IntEnum):
    # Internally we work with the enum member NONE because it is
    # way nicer to work with instead of union with None everywhere.
    # In the database NONE here is actually NULL. This lets us
    # enforce a unique constraint on the kind, since NULL must not
    # be unique where a unique constraint is enforced.
    NONE = 0

    # 1 to 8: Task Attribute Kinds
    NAME = 1
    ALIAS = 2
    ID = 3

    # 9 to 16: User Attribute Kinds
    GIVEN_AT = 9
    GIVEN_BY = 10

    @property
    def type(self) -> AttributeType:
        """Will throw for NONE!"""

        match self:
            case AttributeKind.ID | AttributeKind.NAME | AttributeKind.ALIAS:
                return AttributeType.TASK

            case AttributeKind.GIVEN_AT | AttributeKind.GIVEN_BY:
                return AttributeType.USER

            case AttributeKind.NONE:
                raise ValueError("I told you...")

            case _:
                t.assert_never(self)

@enum.verify(enum.UNIQUE, enum.CONTINUOUS)
class AttributeSlotType(enum.IntEnum):
    BOOLEAN = 1
    INTEGER = 2
    DECIMAL = 3
    STRING = 4

    @property
    def python_type(self) -> type[SlotTypeT]:
        match self:
            case AttributeSlotType.BOOLEAN:
                return bool
            case AttributeSlotType.INTEGER:
                return int
            case AttributeSlotType.DECIMAL:
                return decimal.Decimal
            case AttributeSlotType.STRING:
                return str
            case _:
                t.assert_never(self)
