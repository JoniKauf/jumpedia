from dataclasses import dataclass
from functools import cached_property
import discord as dc

from adapters._base_adapter import BaseAdapter
from adapters._jumpedia import JumpediaAdapter
from adapters._users.discord_user import DiscordUserAdapter
from adapters._discord_server import DiscordServerAdapter
from errors.feedback import feedbacks
from ranks.server_rank import ServerRank


def _require_server(server: dc.Guild | None) -> dc.Guild:
    if server is None:
        raise feedbacks.temp("Server is None")
    
    return server


@dataclass(frozen=True)
class InteractionAdapter(BaseAdapter):
    _interaction: dc.Interaction

    def __post_init__(self) -> None:
        # If a user interacts with Jumpedia, we want to save them.
        #
        # This action basically counts as registering and if somebody ever wants
        # to find out something about this user, then as long as they ever
        # used a single jumpedia command, they will find information.
        self.jumpedia.get_or_create_current_jumpedia_user()

    @cached_property
    def discord_user(self) -> DiscordUserAdapter:
        user_or_member = self._interaction.user
        
        if isinstance(user_or_member, dc.Member):
            return DiscordUserAdapter(user_or_member._user)
        
        return DiscordUserAdapter(user_or_member)
    
    @cached_property
    def discord_server(self) -> DiscordServerAdapter:
        server = _require_server(self._interaction.guild)

        assert isinstance(self._interaction.user, dc.Member)

        return DiscordServerAdapter(
            server,
            self._interaction.user
        )
        
    
    @cached_property
    def jumpedia(self) -> JumpediaAdapter:
        return JumpediaAdapter(self)