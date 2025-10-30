import typing as t

type AnyRankT = JumpediaRank | CommunityRank | ServerRank

import functools
import typing as t
from dataclasses import dataclass


@functools.total_ordering
@dataclass(frozen=True)
class BaseRank:
    SORTED: t.ClassVar[tuple[t.Self, ...]]
    _lookup: t.ClassVar[dict[int, t.Self]]

    power: int
    name: str

    def __post_init__(self) -> None:
        if self.power in self.__class__._lookup:
            raise AssertionError("Same power twice")

        self.__class__._lookup[self.power] = self

    def __init_subclass__(cls) -> None:
        cls._lookup = {}
        cls._init()
        super().__init_subclass__()
        # cls._init()

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
    _init_done: t.ClassVar[bool] = False

    DEFAULT: t.ClassVar["CommunityRank"]
    LOWEST: t.ClassVar["CommunityRank"]
    HIGHEST: t.ClassVar["CommunityRank"]

    @classmethod
    def _init(cls):
        cls.USER = CommunityRank(0, "User")
        cls.HELPER = CommunityRank(10, "Helper")
        cls.MODERATOR = CommunityRank(20, "Moderator")
        cls.ADMINISTRATOR = CommunityRank(30, "Administrator")
        cls.OWNER = CommunityRank(40, "Owner")

        cls.LOWEST = cls.USER
        cls.HIGHEST = cls.OWNER
        cls.DEFAULT = cls.LOWEST

        cls._create_sorted()


@dataclass(frozen=True)
class JumpediaRank(BaseRank):
    _init_done: t.ClassVar[bool] = False

    DEFAULT: t.ClassVar["JumpediaRank"]
    LOWEST: t.ClassVar["JumpediaRank"]
    HIGHEST: t.ClassVar["JumpediaRank"]

    @classmethod
    def _init(cls) -> None:
        cls.JUMPEDIA_USER = JumpediaRank(0, "None")
        cls.META_ADMIN = JumpediaRank(100, "Meta Administrator")
        cls.JONIKAUF = JumpediaRank(200, "JoniKauf")

        cls.LOWEST = cls.JUMPEDIA_USER
        cls.HIGHEST = cls.JONIKAUF
        cls.DEFAULT = cls.LOWEST

        cls._create_sorted()


@dataclass(frozen=True)
class ServerRank(BaseRank):
    _init_done: t.ClassVar[bool] = False

    DEFAULT: t.ClassVar["ServerRank"]
    LOWEST: t.ClassVar["ServerRank"]
    HIGHEST: t.ClassVar["ServerRank"]

    @classmethod
    def _init(cls):
        cls.SERVER_MEMBER = ServerRank(0, "Member")
        cls.SERVER_ADMINISTRATOR = ServerRank(10, "Server Administrator")
        cls.SERVER_OWNER = ServerRank(20, "Server Owner")

        cls.LOWEST = cls.SERVER_MEMBER
        cls.HIGHEST = cls.SERVER_OWNER
        cls.DEFAULT = cls.LOWEST

        cls._create_sorted()


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
