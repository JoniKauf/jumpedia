

import functools
from typing import NamedTuple, Self, TYPE_CHECKING
import discord as dc

from discordtools import errors, feedbackerrors as fbe
from structures.context import Context

_init_module_done: bool = False


@functools.total_ordering
class _Rank:
    def __init__(self, power: int, name: str) -> None:
        if _init_module_done:
            raise errors.ProgrammingError("module init already done")

        self.power = power
        self.name = name

        self.__class__._lookup[power] = self

    def __init_subclass__(cls) -> None:
        cls._lookup: dict[int, Self] = {}

    @classmethod
    def get(cls, power: int) -> Self:
        return cls._lookup[power]

    def __lt__(self, value: '_Rank') -> bool:
        if type(self) != type(value):
            raise errors.ProgrammingError("cannot compare different rank types")
        return self.power < value.power
    
    def __eq__(self, value: object) -> bool:
        return self is value
    
    def __str__(self) -> str:
        return self.name
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.power, self.name})"
    
    
    

class UserRank(_Rank):
    @classmethod
    def _init(cls):
        if _init_module_done:
            raise errors.ProgrammingError()
        
        cls.USER = UserRank(0, "User")
        cls.HELPER = UserRank(1, "Helper")
        cls.MODERATOR = UserRank(2, "Moderator")
        cls.ADMINISTRATOR = UserRank(3, "Administrator")
        cls.OWNER = UserRank(4, "Owner")
        cls.JONIKAUF = UserRank(100, "JoniKauf")


class ServerRank(_Rank):
    @classmethod
    def _init(cls):
        if _init_module_done:
            raise errors.ProgrammingError()
        
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

def permitted(
    ctx: Context,
    user_id: int,
    min_user_rank: UserRank = UserRank.JONIKAUF,
    min_server_rank: ServerRank = ServerRank.UNREACHABLE,
    user_rank: UserRank | None = None,
    server_rank: ServerRank | None = None
) -> tuple[bool, UserRank, ServerRank]:
    from people.user import User

    still_permitted: bool = True
    
    server_rank = server_rank or get_server_rank(ctx.interaction.user)

    if server_rank < min_server_rank:
        still_permitted = False
    
    try:
        user_rank = user_rank or User.get_other(ctx, user_id).
    except fbe.PersonDoesNotExist:
        user_rank = USER_RANKS.USER

    if still_permitted and user_rank < min_user_rank:
        still_permitted = False
    
    return still_permitted, user_rank, server_rank 


_init_module_done = True