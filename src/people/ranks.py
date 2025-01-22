

import functools
from typing import NamedTuple, Self
import discord as dc

from discordtools import errors, feedbackerrors as fbe
from people import users

_init_module_done: bool = False

@functools.total_ordering
class _Rank:
    _identifiers: dict[int | str, '_Rank'] = {}

    def __init__(self, power: int, name: str) -> None:
        if _init_module_done:
            raise errors.ProgrammingError("module init already done")
        if power in self.__class__._identifiers:
            raise errors.ProgrammingError("power used twice")
        if name in self.__class__._identifiers:
            raise errors.ProgrammingError("name used twice")

        self.__class__._identifiers |= {power: self, name.casefold(): self}

        self.power = power
        self.name = name

    def __lt__[T: _Rank](self: T, value: T) -> bool:
        if type(self) != type(value):
            raise errors.ProgrammingError("cannot compare different rank types")
        return self.power < value.power
    
    def __eq__[T: _Rank](self: T, value: T) -> bool:
        return self is value
    
    @classmethod
    def get(cls, rank: int | str) -> Self:
        # possibly raises KeyError
        return cls._identifiers[
            rank.casefold() if
            isinstance(rank, str) else 
            rank
        ] # type: ignore
    
class UserRank(_Rank):
    ...

class ServerRank(_Rank):
    ...


class USER_RANKS(NamedTuple):
    USER = UserRank(0, "User")
    HELPER = UserRank(1, "Helper")
    MODERATOR = UserRank(2, "Moderator")
    ADMINISTRATOR = UserRank(3, "Administrator")
    OWNER = UserRank(4, "Owner")
    JONIKAUF = UserRank(5, "JoniKauf")

class SERVER_RANKS(NamedTuple):
    MEMBER = ServerRank(0, "Member")
    SERVER_ADMINISTRATOR = ServerRank(1, "Server Administrator")
    SERVER_OWNER = ServerRank(2, "Server Owner")

    # If we want to not allow any server ranks
    UNREACHABLE = ServerRank(3, "Unreachable")


def get_server_rank(dc_user: dc.User) -> ServerRank:
    if not isinstance(dc_user, dc.Member):
        return SERVER_RANKS.MEMBER
    
    if dc_user.id == dc_user.guild.owner_id:
        return SERVER_RANKS.SERVER_OWNER
    
    if dc_user.guild_permissions.administrator:
        return SERVER_RANKS.SERVER_ADMINISTRATOR
    
    return SERVER_RANKS.MEMBER


def permitted(
    dc_user: dc.User,
    other_user_id: str | int,
    min_user_rank: UserRank = USER_RANKS.JONIKAUF,
    min_server_rank: ServerRank = SERVER_RANKS.UNREACHABLE
) -> bool:
    if min_server_rank > SERVER_RANKS.MEMBER:
        if get_server_rank(dc_user) < min_server_rank:
            return False
            
    return users.User.get(other_user_id).rank >= min_user_rank

_init_module_done = True