import functools
import typing as t
from abc import abstractmethod
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
        super().__init_subclass__()
        cls._lookup = {}
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
