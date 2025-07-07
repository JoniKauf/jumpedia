from dataclasses import dataclass
from functools import cached_property
from adapters._base_adapter import BaseAdapter
import discord as dc

from adapters._discord.user import UserAdapter
from adapters.interaction import InteractionAdapter
from errors.feedback import feedbacks
from ranks.server_rank import ServerRank


@dataclass(frozen=True)
class ServerAdapter(BaseAdapter):
    _server: dc.Guild

    interaction: InteractionAdapter

    @property
    def id(self) -> int:
        return self._server.id