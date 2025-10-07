import typing as t

import discord_ as dc

from .. import BaseAdapter

if t.TYPE_CHECKING:
    from ..interaction import InteractionAdapter


class ServerAdapter(BaseAdapter):
    _server: dc.Guild

    interaction: InteractionAdapter

    @property
    def id(self) -> int:
        return self._server.id
