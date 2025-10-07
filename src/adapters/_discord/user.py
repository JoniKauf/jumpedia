import typing as t

import discord_ as dc

from .. import BaseAdapter

if t.TYPE_CHECKING:
    from ..interaction import InteractionAdapter


class UserAdapter(BaseAdapter):
    _user: dc.User

    interaction: InteractionAdapter

    @property
    def id(self) -> int:
        return self._user.id

    @property
    def name(self) -> str:
        return self._user.global_name or self._user.name
