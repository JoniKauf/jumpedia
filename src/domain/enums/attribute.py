import decimal
import enum
import typing as t
from functools import cached_property


@enum.verify(enum.UNIQUE, enum.CONTINUOUS)
class AttributeType(enum.IntEnum):
    STATIC = 1
    TASK = 2
    USER = 3

    @classmethod
    def ALL(cls) -> set[AttributeType]:
        return {cls.STATIC, cls.TASK, cls.USER}
    
    @classmethod
    def NON_STATIC(cls) -> set[AttributeType]:
        return {cls.TASK, cls.USER}
    
    @classmethod
    def NON_USER(cls) -> set[AttributeType]:
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

    @cached_property
    def type(self) -> type:
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
