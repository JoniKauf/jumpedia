import time
from dataclasses import field
from functools import cached_property

import discord as dc
import mariadb

from structures.jumpedia import Jumpedia, JumpediaLimits
from utils import orm, secret
from utils.rank import JumpediaRank

from . import BaseAdapter
from ._jumpedia import JumpediaAdapter
from ._server import ServerAdapter
from ._user import ServerMemberAdapter, UserAdapter


def _require_member(user_or_member: dc.User | dc.Member) -> dc.Member:
    from dc_utils.errors import FeedbackError

    if isinstance(user_or_member, dc.User):
        raise FeedbackError(
            "Not On Server", t"You must execute this command on a server!"
        )

    return user_or_member


def is_joni(interaction: dc.Interaction) -> bool:
    return interaction.user.id == 679564566769827841


_CONN: mariadb.Connection | None = None


def _get_connection(*, meta: bool = False) -> mariadb.Connection:
    # Meta is used at startup. Do not do checks and caching and so on.
    if meta:
        data = secret.listen().DATABASE_CONNECTION_DATA | {"db": None}
        return mariadb.connect(**data)

    global _CONN

    if _CONN is not None:
        if _CONN.open:
            return _CONN

        try:
            _CONN.close()
        except mariadb.ProgrammingError:
            pass

    wait: float = 0.01
    TRIES = 6

    for i in range(TRIES):
        try:
            _CONN = mariadb.connect(**secret.listen().DATABASE_CONNECTION_DATA)
        except mariadb.Error:
            if i < TRIES - 1:
                time.sleep(wait)
                wait *= 2
        else:
            return _CONN

    raise ConnectionError("Could not reach Jumpedia database!!")


def _get_cursor_adapter(*, meta: bool = False) -> orm.Cursor:
    return orm.Cursor(conn := _get_connection(meta=meta), conn.cursor(dictionary=True))


_META_C = _get_cursor_adapter(meta=True)

_THE_ONE_PIECE: Jumpedia = Jumpedia(
    id=1,
    limits=JumpediaLimits(
        community_name_length_max=64,
        list_name_length_max=64,
        user_name_length_max=32,  # Discord limit
        attribute_syn_length_max=64,
        attribute_task_value_slot_length_max=255,
    ),
    db_name="jumpedia",
    meta_c=_META_C,
    get_c=lambda: _get_cursor_adapter(),
)

del _META_C


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
                JumpediaRank.JONIKAUF if is_joni(self._o) else None
            ),
        )

    @property
    def dc(self) -> dc.Interaction:
        return self._o

    # CACHE CURSOR; WE WANT THE SAME OBJECT!!
    @cached_property
    def _c(self) -> orm.Cursor:  # type: ignore
        return _get_cursor_adapter()

    @cached_property
    def current_server(self) -> ServerAdapter:
        user = _require_member(self._o.user)
        return ServerAdapter(user.guild, self)

    @cached_property
    def current_user(self) -> UserAdapter:
        user_or_member = self._o.user

        if isinstance(user_or_member, dc.Member):
            return UserAdapter(user_or_member._user, self)

        return UserAdapter(user_or_member, self)

    @cached_property
    def current_member(self) -> ServerMemberAdapter:
        member = _require_member(self._o.user)
        return ServerMemberAdapter(member, self.current_server, self.current_user)

    @cached_property
    def jumpedia(self) -> JumpediaAdapter:
        return JumpediaAdapter(_THE_ONE_PIECE, self)

    def save_changes(self) -> None:
        self._c.commit()
