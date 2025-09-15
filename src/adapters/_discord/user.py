import discord as dc
from adapters import BaseAdapter
from adapters.interaction import InteractionAdapter

class UserAdapter(BaseAdapter):
    _user: dc.User

    interaction: InteractionAdapter

    @property
    def id(self) -> int:
        return self._user.id
    
    @property
    def name(self) -> str:
        return (
            self._user.global_name 
            or self._user.name
        )