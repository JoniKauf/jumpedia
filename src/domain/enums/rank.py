import enum


class CommunityRank(enum.Enum):
    USER = 0
    HELPER = 1
    MODERATOR = 2
    ADMINISTRATOR = 3
    OWNER = 4

    LOWEST = USER
    HIGHEST = OWNER
    DEFAULT = LOWEST

    def __bool__(self) -> bool:
        return bool(self.value)


class MetaRank(enum.Enum):
    USER = 0
    ADMINISTRATOR = 1
    JONIKAUF = 2

    LOWEST = USER
    HIGHEST = JONIKAUF
    DEFAULT = LOWEST

    def __bool__(self) -> bool:
        return bool(self.value)


class ServerRank(enum.Enum):
    USER = 0
    ADMINISTRATOR = 1
    OWNER = 2

    LOWEST = USER
    HIGHEST = OWNER
    DEFAULT = LOWEST

    def __bool__(self) -> bool:
        return bool(self.value)


type AnyRankT = MetaRank | CommunityRank | ServerRank
