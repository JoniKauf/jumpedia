import typing as t

import discord as dc

from .. import BaseAdapter

if t.TYPE_CHECKING:
    from ..interaction import InteractionAdapter


class UserAdapter(BaseAdapter[dc.User]):
    interaction: InteractionAdapter

    @property
    def id(self) -> int:
        return self._s.id

    @property
    def name(self) -> str:
        return self._s.global_name or self._s.name
