import typing as t

import discord as dc

from utils import orm

from . import BaseAdapter

if t.TYPE_CHECKING:
    from .interaction import InteractionAdapter


class ServerAdapter(BaseAdapter[dc.Guild]):
    interaction: InteractionAdapter

    @property
    def _c(self) -> orm.Cursor:
        return self.interaction._c

    @property
    def id(self) -> int:
        return self._o.id
