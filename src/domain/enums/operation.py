import enum


class Operation(enum.Enum):
    REPLACE = enum.auto()
    COMBINE_OVERRIDE_ON_COLLISION = enum.auto()
    COMBINE_ERROR_ON_COLLISION = enum.auto()
