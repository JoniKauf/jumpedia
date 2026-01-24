import enum
import functools
import typing as t
from string.templatelib import Template

from utils import text


class _BaseRankMeta(enum.EnumMeta):
    @property
    def type_name(cls) -> str:
        return text.pascal_to_snake(cls.__name__, delim=" ")


@functools.total_ordering
class _BaseRank(enum.Enum, metaclass=_BaseRankMeta):
    def __lt__(self, value: t.Self | JumpediaRank) -> bool:
        if not isinstance(value, self.__class__ | JumpediaRank):
            return NotImplemented

        return self.value < value.value

    def __str__(self) -> str:
        return self.name

    def __bool__(self) -> bool:
        return bool(self.value)

    def __hash__(self) -> int:
        return hash(self.value)

    @classmethod
    def get(cls, power: int) -> t.Self:
        for elem in cls:  # type: ignore
            if elem.value == power:
                return elem

        raise ValueError(power)

    def mention(self, title: bool = False) -> Template:
        type_name = type(self).type_name
        type_name = type_name.title() if title else type_name.lower()

        return t"{type_name} {self:,}"


class CommunityRank(_BaseRank):
    USER = 0
    HELPER = 10
    MODERATOR = 20
    ADMINISTRATOR = 30
    OWNER = 40

    LOWEST = USER
    HIGHEST = OWNER
    DEFAULT = LOWEST


class JumpediaRank(_BaseRank):
    def __lt__(self, value: t.Self | CommunityRank) -> bool:  # type: ignore
        if not isinstance(value, self.__class__ | CommunityRank):
            return NotImplemented

        return self.value < value.value

    USER = 0
    META_ADMINISTRATOR = 100
    JONIKAUF = 200

    LOWEST = USER
    HIGHEST = JONIKAUF
    DEFAULT = LOWEST


class ServerRank(_BaseRank):
    USER = 0
    ADMINISTRATOR = 10
    OWNER = 20

    LOWEST = USER
    HIGHEST = OWNER
    DEFAULT = LOWEST


type AnyRankT = JumpediaRank | CommunityRank | ServerRank


def get_offset_rank(base_rank: AnyRankT, offset: int) -> AnyRankT:
    """
    This hierarchy is kind of confusing:

    Meta ranks are the most powerful because they extend across
    all of Jumpedia. This means that any meta rank is more powerful
    than any server or community rank.

    A server rank has no meaning to Jumpedia besides being able to
    manage HOW a Community is on a server, but not the internals
    of the Community.

    When we go backwards, so we ask the questions about what
    is LESS powerful than a meta rank, we go down the community
    ranks, because these are actually there to manage the Community.
    """

    if isinstance(base_rank, (JumpediaRank, CommunityRank)):
        scale = tuple(CommunityRank) + tuple(JumpediaRank)[1:]
    else:
        scale = tuple(ServerRank) + tuple(JumpediaRank)[1:]

    idx = scale.index(base_rank) + offset

    if idx < 0:
        return scale[0]

    if idx >= len(scale):
        return scale[-1]

    return scale[idx]
