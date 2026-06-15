import enum
import typing as t
from functools import cached_property


class AttributeType(enum.Enum):
    STATIC = 1
    TASK = 2
    USER = 3


class AttributeKind(enum.Enum):
    NONE = None
    NAME = 1
    ALIAS = 2
    ID = 3


class AttributeSlotType(enum.Enum):
    BOOL = 1
    INT = 2
    FLOAT = 3
    STR = 4

    @cached_property
    def type(self) -> type:
        match self:
            case AttributeSlotType.BOOL:
                return bool
            case AttributeSlotType.INT:
                return int
            case AttributeSlotType.FLOAT:
                return float
            case AttributeSlotType.STR:
                return str
            case _:
                t.assert_never(self)
