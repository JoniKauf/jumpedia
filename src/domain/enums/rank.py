import enum
import functools


@functools.total_ordering
class CommunityRank(enum.IntEnum):
    USER = 0
    HELPER = 1
    MODERATOR = 2
    ADMINISTRATOR = 3
    OWNER = 4

    LOWEST = USER
    HIGHEST = OWNER
    DEFAULT = LOWEST

    def __lt__(self, other: CommunityRank | JumpediaRank):
        if type(other) is JumpediaRank:
            return other.value > 0
        
        return self.value < other.value


@functools.total_ordering
class JumpediaRank(enum.IntEnum):
    USER = 0
    META_ADMINISTRATOR = 1
    JONIKAUF = 2

    LOWEST = USER
    HIGHEST = JONIKAUF
    DEFAULT = LOWEST

    def __lt__(self, other: ServerRank | CommunityRank | JumpediaRank):
        if type(other) is JumpediaRank:
            return self.value < other.value
        
        return self.value > 0


@functools.total_ordering
class ServerRank(enum.IntEnum):
    USER = 0
    ADMINISTRATOR = 1
    OWNER = 2

    LOWEST = USER
    HIGHEST = OWNER
    DEFAULT = LOWEST

    def __lt__(self, other: ServerRank | JumpediaRank):
        if type(other) is JumpediaRank:
            return other.value > 0
        
        return self.value < other.value


type AnyRankT = JumpediaRank | CommunityRank | ServerRank