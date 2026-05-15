import enum
from functools import cached_property
import typing as t

class Type(enum.IntEnum):
    STATIC = 1
    TASK = 2
    USER = 3

class Kind(enum.IntEnum):
    NAME = 1
    ALIAS = 2
    ID = 3

class SlotType(enum.IntEnum):
    BOOL = 1
    INT = 2
    FLOAT = 3
    STR = 4

    @cached_property
    def type(self) -> type:
        match self:
            case SlotType.BOOL: 
                return bool
            case SlotType.INT:
                return int
            case SlotType.FLOAT:
                return float
            case SlotType.STR:
                return str
            case _:
                t.assert_never(self)