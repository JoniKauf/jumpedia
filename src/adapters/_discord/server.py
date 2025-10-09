import typing as t

import discord as dc

from .. import BaseAdapter

if t.TYPE_CHECKING:
    from ..interaction import InteractionAdapter


class ServerAdapter(BaseAdapter):
    _server: dc.Guild

    interaction: InteractionAdapter

    @property
    def id(self) -> int:
        return self._server.id
    
    @property
    def name(self) -> str:
        return self._server.name
