import discord as dc

from adapters import BaseAdapter
from adapters.interaction import InteractionAdapter

class ServerAdapter(BaseAdapter):
    _server: dc.Guild

    interaction: InteractionAdapter

    @property
    def id(self) -> int:
        return self._server.id