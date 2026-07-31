import enum


class AliasEditMode(enum.Enum):
    REPLACE = enum.auto()
    COMBINE_OVERRIDE_ON_COLLISION = enum.auto()
    COMBINE_ERROR_ON_COLLISION = enum.auto()


class CollectionEditMode(enum.Enum):
    REPLACE = enum.auto()
    COMBINE_ERROR_ON_ANY_SYN_COLLISION = enum.auto()


class FieldMappingEditMode(enum.Enum):
    REPLACE = enum.auto()
    COMBINE_OVERRIDE_ON_COLLISION = enum.auto()
    COMBINE_ERROR_ON_COLLISION = enum.auto()
