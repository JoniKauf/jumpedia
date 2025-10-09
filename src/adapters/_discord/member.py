from functools import cached_property

import discord as dc

from ...ranks import ServerRank
from .. import BaseAdapter
from .server import ServerAdapter
from .user import UserAdapter


class MemberAdapter(BaseAdapter):
    _member: dc.Member

    server: ServerAdapter
    user: UserAdapter

    @cached_property
    def server_rank(self) -> ServerRank:
        if self._member == self.server._server.owner:
            return ServerRank.SERVER_OWNER

        if self._member.guild_permissions.administrator:
            return ServerRank.SERVER_ADMINISTRATOR

        return ServerRank.SERVER_MEMBER
