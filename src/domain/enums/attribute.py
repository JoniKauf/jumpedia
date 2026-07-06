import decimal
import enum
import typing as t
from functools import cached_property


@enum.verify(enum.UNIQUE, enum.CONTINUOUS)
class AttributeType(enum.IntEnum):
    STATIC = 1
    TASK = 2
    USER = 3

    type StaticT = t.Literal[AttributeType.STATIC]
    type TaskT = t.Literal[AttributeType.TASK]
    type UserT = t.Literal[AttributeType.USER]

    type NonUserT = StaticT | TaskT
    type NonStaticT = TaskT | UserT
    type AllT = StaticT | TaskT | UserT

    @t.overload
    def as_set(self: StaticT) -> t.AbstractSet[StaticT]:
        return {self}

    @t.overload
    def as_set(self: TaskT) -> t.AbstractSet[TaskT]:
        return {self}

    @t.overload
    def as_set(self: UserT) -> t.AbstractSet[UserT]:
        return {self}

    def as_set(  # pyright: ignore[reportInconsistentOverload]
        self,
    ) -> t.AbstractSet[t.Self]:
        return {self}

    @classmethod
    def ALL(cls) -> t.AbstractSet[AllT]:
        return {cls.STATIC, cls.TASK, cls.USER}

    @classmethod
    def NON_STATIC(cls) -> t.AbstractSet[TaskT | UserT]:
        return {cls.TASK, cls.USER}

    @classmethod
    def NON_USER(cls) -> t.AbstractSet[StaticT | TaskT]:
        return {cls.STATIC, cls.TASK}


@enum.verify(enum.UNIQUE, enum.CONTINUOUS)
class AttributeKind(enum.IntEnum):
    NONE = 0
    NAME = 1
    ALIAS = 2
    ID = 3


@enum.verify(enum.UNIQUE, enum.CONTINUOUS)
class AttributeSlotType(enum.IntEnum):
    BOOLEAN = 1
    INTEGER = 2
    DECIMAL = 3
    STRING = 4

    @property
    def type(self) -> type[SlotTypeT]:
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

    type SlotTypeT = bool | int | decimal.Decimal | str