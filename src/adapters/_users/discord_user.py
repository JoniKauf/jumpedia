from dataclasses import dataclass
import discord as dc
from adapters._base_adapter import BaseAdapter


@dataclass(frozen=True)
class DiscordUserAdapter(BaseAdapter):
    _user: dc.User

    @property
    def user_id(self) -> int:
        return self._user.id
    
    @property
    def user_name(self) -> str:
        return (
            self._user.global_name 
            or self._user.name
        )