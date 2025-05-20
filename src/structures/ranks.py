

from dataclasses import dataclass
import functools
from typing import ClassVar, Self
from database import queries
from discordtools import errors
import discord as dc

from structures.context import Context

type AnyRank = MetaRank | CommunityRank | GuildRank

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
    _init_done: bool = False

    DEFAULT: ClassVar['MetaRank']
    LOWEST: ClassVar['MetaRank']
    HIGHEST: ClassVar['MetaRank']

    @classmethod
    def _init(cls) -> None:
        cls.NONE = MetaRank(0, "None")
        cls.META_ADMIN = MetaRank(10, "Meta Admin")
        cls.JONIKAUF = MetaRank(10 ** 6, "JoniKauf")

        cls.LOWEST = cls.NONE
        cls.HIGHEST = cls.JONIKAUF
        cls.DEFAULT = cls.LOWEST
    

@dataclass(frozen=True)
class CommunityRank(_RankBase):
    _init_done: bool = False

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

        cls.LOWEST = cls.LOWEST
        cls.HIGHEST = cls.OWNER
        cls.DEFAULT = cls.USER
    

@dataclass(frozen=True)
class GuildRank(_RankBase):
    _init_done: bool = False

    DEFAULT: ClassVar['GuildRank']
    LOWEST: ClassVar['GuildRank']
    HIGHEST: ClassVar['GuildRank']

    @classmethod
    def _init(cls):
        cls.MEMBER = GuildRank(0, "Member")
        cls.SERVER_ADMINISTRATOR = GuildRank(1, "Server Administrator")
        cls.GUILD_OWNER = GuildRank(2, "Server Owner")

        cls.LOWEST = cls.MEMBER
        cls.HIGHEST = cls.GUILD_OWNER
        cls.DEFAULT = cls.LOWEST

    @classmethod
    def get_from_discord_user(cls, dc_user: dc.User | dc.Member) -> 'GuildRank':
        if not isinstance(dc_user, dc.Member):
            return GuildRank.MEMBER
        
        if dc_user.id == dc_user.guild.owner_id:
            return GuildRank.GUILD_OWNER
        
        if dc_user.guild_permissions.administrator:
            return GuildRank.SERVER_ADMINISTRATOR
        
        return GuildRank.MEMBER


def _init():
    for cls in _RankBase.__subclasses__():
        cls._init()
        cls._init_done = True
        
_init()