

import discord as dc

from dataclasses import dataclass
from typing import ClassVar

from structures.ranks.abstract_rank import AbstractRank


@dataclass(frozen=True)
class ServerRank(AbstractRank):
    _init_done: ClassVar[bool] = False

    DEFAULT: ClassVar['ServerRank']
    LOWEST: ClassVar['ServerRank']
    HIGHEST: ClassVar['ServerRank']

    @classmethod
    def _init(cls):
        super()._init()
        
        cls.MEMBER = ServerRank(0, "Member")
        cls.SERVER_ADMINISTRATOR = ServerRank(10, "Server Administrator")
        cls.SERVER_OWNER = ServerRank(20, "Server Owner")

        cls.LOWEST = cls.MEMBER
        cls.HIGHEST = cls.SERVER_OWNER
        cls.DEFAULT = cls.LOWEST

        cls._create_sorted()

    @classmethod
    def get_from_discord_user(cls, dc_user: dc.User | dc.Member) -> 'ServerRank':
        if not isinstance(dc_user, dc.Member):
            return ServerRank.MEMBER
        
        if dc_user.id == dc_user.guild.owner_id:
            return ServerRank.SERVER_OWNER
        
        if dc_user.guild_permissions.administrator:
            return ServerRank.SERVER_ADMINISTRATOR
        
        return ServerRank.MEMBER
    

ServerRank._init()