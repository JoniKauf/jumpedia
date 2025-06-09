

from abc import abstractmethod
from dataclasses import dataclass
import functools
from typing import ClassVar, Iterator, Self

from structures.abstract_structure import AbstractStructure


@functools.total_ordering
@dataclass(frozen=True)
class AbstractRank:
    _init_done: ClassVar[bool] = False
    SORTED: ClassVar[tuple[Self, ...]]

    power: int
    name: str
    
    def __post_init__(self) -> None:
        if self._init_done:
            raise AssertionError("Init done")

        if self.power in self.__class__._lookup:
            raise AssertionError("Same power twice")
        
        self.__class__._lookup[self.power] = self

    def __init_subclass__(cls) -> None:
        super().__init_subclass__()

        cls._lookup: dict[int, Self] = {}

    @property
    def identity(self) -> tuple[int, ...]:
        return (self.power,)

    @classmethod
    def _create_sorted(cls) -> None:
        cls.SORTED = tuple(
            sorted(cls._lookup.values(), key=lambda rank: rank.power)
        )

    @abstractmethod
    @classmethod
    def _init(cls) -> None:
        if cls == AbstractRank:
            raise NotImplementedError()
        
        cls._init_done = True


    @classmethod
    def get(cls, power: int) -> Self:
        return cls._lookup[power]
    
    @classmethod
    def iter(cls) -> Iterator[Self]:
        return iter(cls.SORTED)
    
    def __lt__(self, value: Self) -> bool:
        if type(self) != type(value):
            raise AssertionError("Cannot compare 2 different types of ranks")
        
        return self.power < value.power
    
    def __eq__(self, value: object) -> bool:
        return self is value
    
    def __str__(self) -> str:
        return self.name
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.power}, {self.name})"
    
    def __bool__(self) -> bool:
        return bool(self.power)

    @property
    @abstractmethod
    def parent(self) -> AbstractStructure:
        """The structure that handles the creation, deletion or editing of this structure."""

