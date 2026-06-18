import enum


@enum.verify(enum.CONTINUOUS)
class CommunityRank(enum.IntEnum):
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


@enum.verify(enum.CONTINUOUS)
class MetaRank(enum.IntEnum):
    USER = 0
    ADMINISTRATOR = 1
    JONIKAUF = 2

    LOWEST = USER
    HIGHEST = JONIKAUF
    DEFAULT = LOWEST

    def __bool__(self) -> bool:
        return bool(self.value)


@enum.verify(enum.CONTINUOUS)
class ServerRank(enum.IntEnum):
    USER = 0
    ADMINISTRATOR = 1
    OWNER = 2

    LOWEST = USER
    HIGHEST = OWNER
    DEFAULT = LOWEST

    def __bool__(self) -> bool:
        return bool(self.value)


type AnyRankT = MetaRank | CommunityRank | ServerRank
