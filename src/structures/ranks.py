

import functools
from typing import Self
from discordtools import errors
import discord as dc

@functools.total_ordering
class _RankBase:
    _init_done: bool = False

    def __init__(self, power: int, name: str) -> None:
        if self._init_done:
            raise errors.ProgrammingError("module init already done")

        self.power = power
        self.name = name

        if self.power in self.__class__._lookup:
            raise errors.ProgrammingError("same power twice")
        
        self.__class__._lookup[power] = self

    def __init_subclass__(cls) -> None:
        cls._lookup: dict[int, Self] = {}

    @classmethod
    def _init(cls) -> None:
        raise NotImplementedError()

    @classmethod
    def get(cls, power: int) -> Self:
        return cls._lookup[power]

    def __lt__(self, value: '_RankBase') -> bool:
        if type(self) != type(value):
            raise errors.ProgrammingError("cannot compare different rank types")
        return self.power < value.power
    
    def __eq__(self, value: object) -> bool:
        return self is value
    
    def __str__(self) -> str:
        return self.name
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.power}, {self.name})"
    

class UserRank(_RankBase):
    _init_done: bool = False

    @classmethod
    def _init(cls):
        cls.USER = UserRank(0, "User")
        cls.HELPER = UserRank(1, "Helper")
        cls.MODERATOR = UserRank(2, "Moderator")
        cls.ADMINISTRATOR = UserRank(3, "Administrator")
        cls.OWNER = UserRank(4, "Owner")
        cls.JONIKAUF = UserRank(100, "JoniKauf")


class ServerRank(_RankBase):
    _init_done: bool = False

    @classmethod
    def _init(cls):
        cls.MEMBER = ServerRank(0, "Member")
        cls.SERVER_ADMINISTRATOR = ServerRank(1, "Server Administrator")
        cls.SERVER_OWNER = ServerRank(2, "Server Owner")

        # If we want to not allow any server ranks
        cls.UNREACHABLE = ServerRank(3, "Unreachable")


def get_server_rank(dc_user: dc.User | dc.Member) -> ServerRank:
    if not isinstance(dc_user, dc.Member):
        return ServerRank.MEMBER
    
    if dc_user.id == dc_user.guild.owner_id:
        return ServerRank.SERVER_OWNER
    
    if dc_user.guild_permissions.administrator:
        return ServerRank.SERVER_ADMINISTRATOR
    
    return ServerRank.MEMBER


def _init():
    for cls in _RankBase.__subclasses__():
        cls._init()
        cls._init_done = True
        
_init()