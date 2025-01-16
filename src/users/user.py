import functools
from database import queries
from typing import NamedTuple, Optional as Opt

from discordtools import errors

@functools.total_ordering
class Rank:
    _powers: set[int] = set()
    _names: set[str] = set()

    def __init__(self, power: int, name: str) -> None:
        if power in self.__class__._powers:
            raise errors.ProgrammingError("power used twice")
        if name in self.__class__._names:
            raise errors.ProgrammingError("power used twice")

        self.__class__._powers.add(power)
        self.__class__._names.add(name)

        self.power = power
        self.name = name

    def __lt__(self, value: 'Rank') -> bool:
        return self.power < value.power
    
    def __eq__(self, value: 'Rank') -> bool:
        return self is value


class RANKS(NamedTuple):
    USER = Rank(0, "User")
    HELPER = Rank(1, "Helper")
    MODERATOR = Rank(2, "Moderator")
    ADMINISTRATOR = Rank(3, "Administrator")
    OWNER = Rank(4, "Owner")


class User:
    def __init__(self, id: int, rank: Rank, custom_name: Opt[str] = None, person_id: Opt[int] = None) -> None:
        pass