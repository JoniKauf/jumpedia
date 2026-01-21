from functools import cached_property
import typing as t

import discord as dc

from utils import orm

from . import BaseAdapter

if t.TYPE_CHECKING:
    from .interaction import InteractionAdapter


class ServerAdapter(BaseAdapter[dc.Guild]):
    interaction: InteractionAdapter

    @cached_property
    def _c(self) -> orm.Cursor:
        return self.interaction._c

    @property
    def id(self) -> int:
        return self._o.id
