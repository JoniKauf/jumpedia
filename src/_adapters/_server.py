import typing as t
from functools import cached_property

import discord as dc

from utils import orm

from . import BaseAdapter

if t.TYPE_CHECKING:
    from .interaction import _InteractionAdapter


class ServerAdapter(BaseAdapter[dc.Guild]):
    interaction: _InteractionAdapter

    @cached_property
    def _c(self) -> orm.Cursor:
        return self.interaction._c

    @property
    def id(self) -> int:
        return self._o.id
