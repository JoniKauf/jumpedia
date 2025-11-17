import typing as t

import discord as dc

from .. import BaseAdapter

if t.TYPE_CHECKING:
    from ..interaction import InteractionAdapter


class ServerAdapter(BaseAdapter[dc.Guild]):
    interaction: InteractionAdapter

    @property
    def id(self) -> int:
        return self._s.id
