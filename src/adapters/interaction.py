from functools import cached_property

import discord as dc

from discord_.errors import FeedbackError
from utils.rank import JumpediaRank

from . import BaseAdapter
from ._jumpedia import _JUMPEDIA, JumpediaAdapter
from ._server import ServerAdapter
from ._user import ServerMemberAdapter, UserAdapter


def _require_member(user_or_member: dc.User | dc.Member) -> dc.Member:
    if isinstance(user_or_member, dc.User):
        raise FeedbackError(
            "Not On Server", t"You must execute this command on a server!"
        )

    return user_or_member


def is_joni(interaction: dc.Interaction) -> bool:
    return interaction.user.id == 679564566769827841


class InteractionAdapter(BaseAdapter[dc.Interaction]):
    def __post_init__(self) -> None:
        # If a user interacts with Jumpedia, we want to save them.
        #
        # This action basically counts as registering and if somebody ever wants
        # to find out something about this user, then as long as they ever
        # used a single jumpedia command, they will find information.
        self.jumpedia.get_or_create_jumpedia_user(
            self.current_user,
            override_jumpedia_rank=(
                JumpediaRank.JONIKAUF if is_joni(self._s) else None
            ),
        )

    @cached_property
    def current_server(self) -> ServerAdapter:
        user = _require_member(self._s.user)
        return ServerAdapter(user.guild, self)

    @cached_property
    def current_user(self) -> UserAdapter:
        user_or_member = self._s.user

        if isinstance(user_or_member, dc.Member):
            return UserAdapter(user_or_member._user, self)

        return UserAdapter(user_or_member, self)

    @cached_property
    def current_member(self) -> ServerMemberAdapter:
        member = _require_member(self._s.user)
        return ServerMemberAdapter(member, self.current_server, self.current_user)

    @cached_property
    def jumpedia(self) -> JumpediaAdapter:
        return JumpediaAdapter(_JUMPEDIA, self)
