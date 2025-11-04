import typing as t
from curses import meta
from dataclasses import field

from src.discord_.errors import FeedbackError
from src.utils import secret
from src.utils.orm import Connector

from ..structures.community import Community
from ..structures.errors import (ServerAlreadyConnectedToCommunityError,
                                 SynAlreadyTakenError)
from ..structures.jumpedia import Jumpedia, JumpediaLimits
from ..utils import text
from . import BaseAdapter, errors
from ._community import CommunityAdapter
from ._discord.user import UserAdapter
from ._user.jumpedia_user import JumpediaUserAdapter

if t.TYPE_CHECKING:
    from adapters.interaction import InteractionAdapter


__conn_data = secret.listen().DATABASE_CONNECTION_DATA

_JUMPEDIA = Jumpedia(
    id=1,
    limits=JumpediaLimits(
        community_name_length_max=64,
        list_name_length_max=64,
        user_name_length_max=32,  # Discord limit
        attribute_syn_length_max=64,
        attribute_task_value_slot_length_max=255,
        attribute_task_value_slot_count_max=32
    ),
    connector=Connector(
        **__conn_data,
        database_name='jumpedia'
    ),
    meta_connector=Connector(
        **__conn_data,
        database_name=None
    )
)

def _require_server_with_community(community: Community | None) -> Community:
    if community is None:
        raise feedbacks.temp("Server isnt connected ot community")

    return community


def _require_community_with_name(name: text.NormStr, jumpedia: Jumpedia) -> Community:
    community = jumpedia.get_community_by_name(name)

    if community is None:
        raise feedbacks.temp(f"Community with the name `{name}` could not be found!")

    return community


class JumpediaAdapter(BaseAdapter):
    interaction: InteractionAdapter
    _jumpedia: Jumpedia = field(init=False, default=_JUMPEDIA)

    # --- Community ---

    def get_communities(self) -> list[CommunityAdapter]:
        return [CommunityAdapter(c, self) for c in self._jumpedia.get_communities()]

    def get_community(self, name: str) -> CommunityAdapter:
        return CommunityAdapter(
            _require_community_with_name(text.raw_to_norm(name), self._jumpedia), self
        )

    def get_current_community(self) -> CommunityAdapter:
        return self.get_community(
            _require_server_with_community(
                self._jumpedia.get_community_by_server_id(
                    self.interaction.current_server.id
                )
            ).real_name
        )

    def create_community(
        self, name: str, initial_list_name: str | None
    ) -> CommunityAdapter:
        jumpedia_user = self.get_or_create_current_jumpedia_user()._jumpedia_user

        try:
            comm = self._jumpedia.create_community(
                raw_name=name,
                creator=jumpedia_user,
                server_id=self.interaction.current_server.id,
            )
        except ServerAlreadyConnectedToCommunityError as e:
            raise FeedbackError(
                "Server Already Connected To A Community",
                t"The server you are on (`{self.interaction.current_server.name}`) "
                t"is already connected to a community (`{e.structure.name}`)!",
            )
        except SynAlreadyTakenError as e:
            raise errors.SynAlreadyTakenFeedbackError(e)

        community = CommunityAdapter(comm, self)

        if initial_list_name is not None:
            try:
                list = community.create_list(initial_list_name)
                community.set_default_selected_list(list.name)
            except Exception as e:
                self.delete_community(name)
                raise e

        return community

    def delete_community(self, name: str) -> None:
        community = _require_community_with_name(text.raw_to_norm(name), self._jumpedia)
        self._jumpedia.delete_community(community.id)

    def delete_current_community(self) -> None:
        self._jumpedia.delete_community(self.get_current_community()._community.id)

    def add_community_to_current_server(self, name: str) -> CommunityAdapter:
        return CommunityAdapter(
            self._jumpedia.add_community_to_server(
                self.get_community(name)._community.id,
                self.interaction.current_server.id,
            ),
            self,
        )

    def remove_community_from_current_server(self) -> CommunityAdapter:
        return CommunityAdapter(
            self._jumpedia.remove_community_from_server(
                self.interaction.current_server._server.id
            ),
            self,
        )

    # --- Jumpedia User ---

    def get_or_create_jumpedia_user(
        self, user: UserAdapter, override_jumpedia_rank: JumpediaRank | None = None
    ) -> JumpediaUserAdapter:
        jumpedia_user = self._jumpedia.get_or_create_jumpedia_user(
            user.id,
            user.name,
            override_jumpedia_rank or JumpediaRank.DEFAULT,
            True,
            override_jumpedia_rank is not None,
        )

        return JumpediaUserAdapter(jumpedia_user, self)

    def get_or_create_current_jumpedia_user(
        self, override_jumpedia_rank: JumpediaRank | None = None
    ) -> JumpediaUserAdapter:
        return self.get_or_create_jumpedia_user(
            self.interaction.current_user, override_jumpedia_rank
        )
