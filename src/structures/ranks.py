

import functools
from typing import Self
from database import queries
from discordtools import errors
import discord as dc

from structures.context import Context

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
    
    def permitted(self, min_required_rank: Self) -> bool:
        if type(self) != type(min_required_rank):
            raise errors.ProgrammingError("cannot compare different rank types")
        
        return self.power >= min_required_rank.power

    
class UserRank(_RankBase):
    _init_done: bool = False

    DEFAULT: 'UserRank'
    LOWEST: 'UserRank'
    HIGHEST: 'UserRank'

    def __init__(self, power: int, name: str, meta: bool) -> None:
        super().__init__(power, name)
        self.meta = meta

    @classmethod
    def _init(cls):
        cls.USER = UserRank(0, "User", False)
        cls.HELPER = UserRank(10, "Helper", False)
        cls.MODERATOR = UserRank(20, "Moderator", False)
        cls.ADMINISTRATOR = UserRank(30, "Administrator", False)
        cls.OWNER = UserRank(40, "Owner", False)

        cls.META_ADMIN = UserRank(50, "Meta Admin", True)
        cls.JONIKAUF = UserRank(10 ** 6, "JoniKauf", True)

        cls.DEFAULT = cls.USER
        cls.LOWEST = cls.USER
        cls.HIGHEST = cls.JONIKAUF

        
        # Assert that all meta ranks are higher than non-meta ranks
        non_meta = max(power for power, rank in cls._lookup.items() if not rank.meta)
        meta = min(power for power, rank in cls._lookup.items() if rank.meta)

        assert non_meta < meta

    @classmethod
    def get_meta_from_user_id(cls, id: int) -> 'UserRank | None':
        from structures.jumpedia import Jumpedia

        result = Jumpedia()._fetch_from_meta_user_table(where=lambda h: f"id = {h|id}")

        return cls.get(result[0]['power']) if result else None

class GuildRank(_RankBase):
    _init_done: bool = False

    DEFAULT: 'GuildRank'
    LOWEST: 'GuildRank'
    HIGHEST: 'GuildRank'

    @classmethod
    def _init(cls):
        cls.MEMBER = GuildRank(0, "Member")
        cls.SERVER_ADMINISTRATOR = GuildRank(1, "Server Administrator")
        cls.GUILD_OWNER = GuildRank(2, "Server Owner")

        cls.DEFAULT = cls.MEMBER
        cls.LOWEST = cls.MEMBER
        cls.HIGHEST = cls.GUILD_OWNER

    @classmethod
    def get_from_discord_user(cls, dc_user: dc.User | dc.Member) -> 'GuildRank':
        if not isinstance(dc_user, dc.Member):
            return GuildRank.MEMBER
        
        if dc_user.id == dc_user.guild.owner_id:
            return GuildRank.GUILD_OWNER
        
        if dc_user.guild_permissions.administrator:
            return GuildRank.SERVER_ADMINISTRATOR
        
        return GuildRank.MEMBER
    
    def permitted(self, user_rank: UserRank, min_required_rank: Self) -> bool:
        if super().permitted(min_required_rank):
            return True
        
        return user_rank.meta


def _init():
    for cls in _RankBase.__subclasses__():
        cls._init()
        cls._init_done = True
        
_init()