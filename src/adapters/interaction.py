import time
from dataclasses import field
from functools import cached_property

import discord as dc
import mariadb

from dc_utils import connect, errors
from structures import db
from structures.jumpedia import Jumpedia
from utils import orm, secret
from utils.rank import JumpediaRank

from . import BaseAdapter
from ._jumpedia import JumpediaAdapter
from ._server import ServerAdapter
from ._user import JumpediaUserAdapter, ServerMemberAdapter, UserAdapter


def is_joni(interaction: dc.Interaction) -> bool:
    return interaction.user.id == 679564566769827841


_THE_ONE_PIECE: Jumpedia | None = None


def _get_or_create_the_one_piece():
    global _THE_ONE_PIECE

    if _THE_ONE_PIECE is None:
        conn_data = secret.listen().DATABASE_CONNECTION_DATA

        _THE_ONE_PIECE = Jumpedia(
            id=1,
            limits={
                "community_name_length_max": 64,
                "list_name_length_max": 64,
                "user_name_length_max": 32,  # Discord limit
                "attribute_syn_length_max": 64,
                "attribute_task_value_slot_length_max": 255,
            },
        )

        db.create_database(
            _THE_ONE_PIECE,
            conn_data["db"],
            lambda: orm.Cursor(
                conn := mariadb.connect(**conn_data | {"db": None}),
                conn.cursor(dictionary=True),
            ),
            lambda: orm.Cursor(
                conn := mariadb.connect(
                    **conn_data
                    | {
                        "db": None,
                        "user": "root",
                        "password": input("Enter mariadb root password: "),
                    }
                ),
                conn.cursor(dictionary=True),
            ),
            connect.get_new_connection_cursor_adapter,
        )

    return _THE_ONE_PIECE


class InteractionAdapter(BaseAdapter[dc.Interaction]):
    ia_jumpedia_user: JumpediaUserAdapter = field(init=False, default=None)  # type: ignore

    def __post_init__(self) -> None:
        # If a user interacts with Jumpedia, we want to save them.
        #
        # This action basically counts as registering and if somebody ever wants
        # to find out something about this user, then as long as they ever
        # used a single jumpedia command, they will find information.
        object.__setattr__(
            self,
            "ia_jumpedia_user",
            self.jumpedia.get_or_create_jumpedia_user(
                self.ia_user,
                override_jumpedia_rank=(
                    JumpediaRank.JONIKAUF if is_joni(self._o) else None
                ),
            ),
        )

    @property
    def dc(self) -> dc.Interaction:
        return self._o

    # CACHE CURSOR; WE WANT THE SAME OBJECT!!
    @cached_property
    def _c(self) -> orm.Cursor:
        return connect.get_new_connection_cursor_adapter()

    @cached_property
    def ia_user(self) -> UserAdapter:
        user_or_member = self.dc.user

        if isinstance(user_or_member, dc.User):
            return UserAdapter(user_or_member, self)

        return UserAdapter(user_or_member._user, self, user_or_member)

    @cached_property
    def ia_server_member(self) -> ServerMemberAdapter:
        return self.ia_user.try_as_member

    @cached_property
    def ia_server(self) -> ServerAdapter:
        return self.ia_server_member.server

    @cached_property
    def jumpedia(self) -> JumpediaAdapter:
        return JumpediaAdapter(_get_or_create_the_one_piece(), self)

    def save_changes(self) -> None:
        self._c.commit()
