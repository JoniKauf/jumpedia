from typing import TYPE_CHECKING
import discord as dc
from adapters import BaseAdapter

if TYPE_CHECKING:
    from adapters.interaction import InteractionAdapter


class UserAdapter(BaseAdapter):
    _user: dc.User

    interaction: InteractionAdapter

    @property
    def id(self) -> int:
        return self._user.id

    @property
    def name(self) -> str:
        return self._user.global_name or self._user.name
