import typing as t

type AnyRankT = JumpediaRank | CommunityRank | ServerRank

import functools
import typing as t
from dataclasses import dataclass


@functools.total_ordering
@dataclass(frozen=True)
class BaseRank:
    DEFAULT: t.ClassVar[t.Self]
    LOWEST: t.ClassVar[t.Self]
    HIGHEST: t.ClassVar[t.Self]

    SORTED: t.ClassVar[tuple[t.Self, ...]]
    _lookup: t.ClassVar[dict[int, t.Self]]

    power: int
    name: str

    def __post_init__(self) -> None:
        if self.power in self.__class__._lookup:
            raise AssertionError("Same power twice")

        self.__class__._lookup[self.power] = self

    def __init_subclass__(cls) -> None:
        super().__init_subclass__()
        cls._lookup = {}
        cls._init()
        cls._create_sorted()

    @classmethod
    def _create_sorted(cls) -> None:
        cls.SORTED = tuple(sorted(cls._lookup.values(), key=lambda rank: rank.power))

    @classmethod
    def _init(cls) -> None:
        pass

    @classmethod
    def get(cls, power: int) -> t.Self:
        return cls._lookup[power]

    @classmethod
    def iter(cls) -> t.Iterator[t.Self]:
        return iter(cls.SORTED)

    def __lt__(self, value: t.Self) -> bool:
        if type(self) is not type(value):
            raise AssertionError("Cannot compare 2 different types of ranks")

        return self.power < value.power

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.power}, {self.name})"

    def __bool__(self) -> bool:
        return bool(self.power)

    def __hash__(self) -> int:
        return hash(self.power)

    def __eq__(self, value: object) -> bool:
        return self is value


@dataclass(frozen=True)
class CommunityRank(BaseRank):
    @classmethod
    def _init(cls) -> None:
        cls.USER = cls(0, "User")
        cls.HELPER = cls(10, "Helper")
        cls.MODERATOR = cls(20, "Moderator")
        cls.ADMINISTRATOR = cls(30, "Administrator")
        cls.OWNER = cls(40, "Owner")

        cls.LOWEST = cls.USER
        cls.HIGHEST = cls.OWNER
        cls.DEFAULT = cls.LOWEST


@dataclass(frozen=True)
class JumpediaRank(BaseRank):
    @classmethod
    def _init(cls) -> None:
        cls.JUMPEDIA_USER = cls(0, "None")
        cls.META_ADMIN = cls(100, "Meta Administrator")
        cls.JONIKAUF = cls(200, "JoniKauf")

        cls.LOWEST = cls.JUMPEDIA_USER
        cls.HIGHEST = cls.JONIKAUF
        cls.DEFAULT = cls.LOWEST


@dataclass(frozen=True)
class ServerRank(BaseRank):
    @classmethod
    def _init(cls):
        cls.SERVER_MEMBER = cls(0, "Member")
        cls.SERVER_ADMINISTRATOR = cls(10, "Server Administrator")
        cls.SERVER_OWNER = cls(20, "Server Owner")

        cls.LOWEST = cls.SERVER_MEMBER
        cls.HIGHEST = cls.SERVER_OWNER
        cls.DEFAULT = cls.LOWEST


def get_offset_rank(base_rank: AnyRankT, offset: int) -> AnyRankT:
    """
    This hierarchy is kind of confusing:

    Any meta rank (besides NONE) is higher than any other rank.
    Meta ranks therefore basically extend the scale of community ranks
    and server ranks at the top.

    If we need to go down from meta ranks, we use community ranks.
    Server ranks are something that only goes one way.
    """

    if isinstance(base_rank, (JumpediaRank, CommunityRank)):
        scale = CommunityRank.SORTED + JumpediaRank.SORTED[1:]
    else:
        scale = ServerRank.SORTED + JumpediaRank.SORTED[1:]

    idx = scale.index(base_rank) + offset

    if idx < 0:
        return scale[0]

    if idx > len(scale) - 1:
        return scale[-1]

    return scale[idx]


def rank_classes_iter() -> t.Iterator[type[AnyRankT]]:
    return iter(BaseRank.__subclasses__())  # type: ignore
