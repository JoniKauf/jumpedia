from typing import TYPE_CHECKING
import discord as dc
from adapters import BaseAdapter

if TYPE_CHECKING:
    from adapters.interaction import InteractionAdapter

class ServerAdapter(BaseAdapter):
    _server: dc.Guild

    interaction: InteractionAdapter

    @property
    def id(self) -> int:
        return self._server.id