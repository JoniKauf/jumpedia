import decimal
import enum
import typing as t

from domain.types.attribute import AnyAttributeTypeT, SlotTypeT, StaticAttributeTypeT, TaskAttributeTypeT, UserAttributeTypeT


@enum.verify(enum.UNIQUE, enum.CONTINUOUS)
class AttributeType(enum.IntEnum):
    STATIC = 1
    TASK = 2
    USER = 3

    @t.overload
    def as_set(self: StaticAttributeTypeT) -> t.AbstractSet[StaticAttributeTypeT]:
        pass

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
        return {cls.STATIC, cls.TASK, cls.USER}

    @classmethod
    def NON_STATIC(cls) -> t.AbstractSet[TaskAttributeTypeT | UserAttributeTypeT]:
        return {cls.TASK, cls.USER}

    @classmethod
    def NON_USER(cls) -> t.AbstractSet[StaticAttributeTypeT | TaskAttributeTypeT]:
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