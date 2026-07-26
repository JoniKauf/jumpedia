import enum


class Concept(enum.Enum):
    ATTRIBUTE = enum.auto()
    ATTRIBUTE_SLOT_TYPE = enum.auto()
    COLLECTION = enum.auto()
    COLLECTION_ENTRY = enum.auto()
    COMMUNITY = enum.auto()
    COMMUNITY_RANK = enum.auto()
    FIELD = enum.auto()
    FIELD_MAPPING = enum.auto()
    FIELD_SLOT = enum.auto()
    LIST = enum.auto()
    MEMBER = enum.auto()
    META_RANK = enum.auto()
    SERVER = enum.auto()
    SERVER_RANK = enum.auto()
    TASK = enum.auto()
    USER = enum.auto()