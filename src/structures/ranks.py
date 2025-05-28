

from dataclasses import dataclass
import functools
from typing import ClassVar, Self
from database import queries
from discordtools import errors
import discord as dc

type AnyRank = MetaRank | CommunityRank | ServerRank

@functools.total_ordering
@dataclass(frozen=True)
class _RankBase:
    _init_done: ClassVar[bool] = False
    
    power: int
    name: str
    
    def __post_init__(self) -> None:
        if self._init_done:
            raise errors.ProgrammingError("module init already done")

        if self.power in self.__class__._lookup:
            raise errors.ProgrammingError("same power twice")
        
        self.__class__._lookup[self.power] = self

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


@dataclass(frozen=True)
class MetaRank(_RankBase):
    _init_done: ClassVar[bool] = False

    DEFAULT: ClassVar['MetaRank']
    LOWEST: ClassVar['MetaRank']
    HIGHEST: ClassVar['MetaRank']

    @classmethod
    def _init(cls) -> None:
        cls.NONE = MetaRank(0, "None")
        cls.META_ADMIN = MetaRank(100, "Meta Admin")
        cls.JONIKAUF = MetaRank(10 ** 6, "JoniKauf")

        cls.LOWEST = cls.NONE
        cls.HIGHEST = cls.JONIKAUF
        cls.DEFAULT = cls.LOWEST
    

@dataclass(frozen=True)
class CommunityRank(_RankBase):
    _init_done: ClassVar[bool] = False

    DEFAULT: ClassVar['CommunityRank']
    LOWEST: ClassVar['CommunityRank']
    HIGHEST: ClassVar['CommunityRank']

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
    

@dataclass(frozen=True)
class ServerRank(_RankBase):
    _init_done: ClassVar[bool] = False

    DEFAULT: ClassVar['ServerRank']
    LOWEST: ClassVar['ServerRank']
    HIGHEST: ClassVar['ServerRank']

    @classmethod
    def _init(cls):
        cls.MEMBER = ServerRank(0, "Member")
        cls.SERVER_ADMINISTRATOR = ServerRank(10, "Server Administrator")
        cls.SERVER_OWNER = ServerRank(20, "Server Owner")

        cls.LOWEST = cls.MEMBER
        cls.HIGHEST = cls.SERVER_OWNER
        cls.DEFAULT = cls.LOWEST

    @classmethod
    def get_from_discord_user(cls, dc_user: dc.User | dc.Member) -> 'ServerRank':
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