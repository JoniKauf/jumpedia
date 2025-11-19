import typing as t
from functools import cached_property

import discord as dc

from utils.rank import ServerRank

from . import BaseAdapter
from ._server import ServerAdapter

if t.TYPE_CHECKING:
    from ._user import ServerUserAdapter


class ServerMemberAdapter(BaseAdapter[dc.Member]):
    server: ServerAdapter
    user: ServerUserAdapter

    @cached_property
    def server_rank(self) -> ServerRank:
        if self._s == self.server._s.owner:
            return ServerRank.SERVER_OWNER

        if self._s.guild_permissions.administrator:
            return ServerRank.SERVER_ADMINISTRATOR

        return ServerRank.SERVER_MEMBER
