from functools import cached_property

import discord as dc

from structures.user.rank import ServerRank

from .. import BaseAdapter
from .server import ServerAdapter
from .user import UserAdapter


class MemberAdapter(BaseAdapter[dc.Member]):
    server: ServerAdapter
    user: UserAdapter

    @cached_property
    def server_rank(self) -> ServerRank:
        if self._s == self.server._s.owner:
            return ServerRank.SERVER_OWNER

        if self._s.guild_permissions.administrator:
            return ServerRank.SERVER_ADMINISTRATOR

        return ServerRank.SERVER_MEMBER
