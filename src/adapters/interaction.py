from functools import cached_property

import discord_ as dc

from ..errors.feedback import feedbacks
from . import BaseAdapter
from ._discord.member import MemberAdapter
from ._discord.server import ServerAdapter
from ._discord.user import UserAdapter
from ._jumpedia import JumpediaAdapter


def _require_member(user_or_member: dc.User | dc.Member) -> dc.Member:
    if isinstance(user_or_member, dc.User):
        raise feedbacks.temp("You must be on a server")

    return user_or_member


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
    def current_server(self) -> ServerAdapter:
        user = _require_member(self._interaction.user)
        return ServerAdapter(user.guild, self)

    @cached_property
    def current_user(self) -> UserAdapter:
        user_or_member = self._interaction.user

        if isinstance(user_or_member, dc.Member):
            return UserAdapter(user_or_member._user, self)

        return UserAdapter(user_or_member, self)

    @cached_property
    def current_member(self) -> MemberAdapter:
        member = _require_member(self._interaction.user)
        return MemberAdapter(member, self.current_server, self.current_user)

    @cached_property
    def jumpedia(self) -> JumpediaAdapter:
        return JumpediaAdapter(self)
