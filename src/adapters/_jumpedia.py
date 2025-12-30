import typing as t

from discord_.errors import FeedbackError
from discord_.utils_ import shortcuts
from structures.community import Community, CommunityLimits
from structures.errors import (
    ServerAlreadyConnectedToCommunityError,
    ServerNotConnectedToACommunityError,
    SynsAlreadyTakenError,
)
from structures.jumpedia import Jumpedia, JumpediaLimits
from utils import secret, text
from utils.orm import Connector
from utils.rank import JumpediaRank

from . import BaseStructureAdapter, errors
from ._community import CommunityAdapter
from ._user import JumpediaUserAdapter, UserAdapter

if t.TYPE_CHECKING:
    from .interaction import InteractionAdapter


__conn_data = secret.listen().DATABASE_CONNECTION_DATA

_JUMPEDIA = Jumpedia(
    id=1,
    limits=JumpediaLimits(
        community_name_length_max=64,
        list_name_length_max=64,
        user_name_length_max=32,  # Discord limit
        attribute_syn_length_max=64,
        attribute_task_value_slot_length_max=255,
    ),
    connector=Connector(**__conn_data, database_name="jumpedia"),
    meta_connector=Connector(**__conn_data, database_name=None),
)


def _require_community_with_name(name: text.NormStr, jumpedia_s: Jumpedia) -> Community:
    community = jumpedia_s.get_community_by_name(name)

    if community is None:
        raise FeedbackError(
            "Community Not Found",
            t"A community with the name `{name}` could not be found!",
        )

    return community


class JumpediaAdapter(BaseStructureAdapter[Jumpedia]):
    interaction: InteractionAdapter

    # --- Community ---

    def get_communities(self) -> list[CommunityAdapter]:
        return [CommunityAdapter(c, self) for c in self._s.get_communities()]

    def get_community(self, name: str) -> CommunityAdapter:
        return CommunityAdapter(
            _require_community_with_name(text.NormStr(name), self._s), self
        )

    def create_community(
        self, name: str, initial_list_name: str | None
    ) -> CommunityAdapter:
        jumpedia_user = shortcuts.get_or_create_specified_or_current_jumpedia_user(self, None)

        try:
            comm = self._s.create_community(
                name=text.RealStr(name),
                server_id=self.interaction.current_server.id,
                creator=jumpedia_user._s,
                limits=CommunityLimits(),
            )
        except ServerAlreadyConnectedToCommunityError as e:
            raise errors.ServerAlreadyConnectedToACommunityFeedbackError(e)
        except SynsAlreadyTakenError as e:
            raise errors.SynsAlreadyTakenFeedbackError(e)

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
        community = _require_community_with_name(text.NormStr(name), self._s)
        self._s.delete_community(community.id)

    def delete_current_community(self) -> None:
        self._s.delete_community(
            shortcuts.get_current_community(self.interaction)._s.id
        )

    def add_community_to_current_server(self, name: str) -> CommunityAdapter:
        try:
            return CommunityAdapter(
                self._s.add_community_to_server(
                    self.get_community(name)._s.id,
                    self.interaction.current_server.id,
                ),
                self,
            )
        except ServerAlreadyConnectedToCommunityError as e:
            raise errors.ServerAlreadyConnectedToACommunityFeedbackError(e)

    def remove_community_from_current_server(self) -> CommunityAdapter:
        try:
            community = self._s.remove_community_from_server(
                self.interaction.current_server._s.id
            )
        except ServerNotConnectedToACommunityError:
            raise errors.ServerNotConnectedToACommunityFeedbackError()

        return CommunityAdapter(community, self)

    # --- Jumpedia User ---

    def get_or_create_jumpedia_user(
        self,
        user: UserAdapter,
        *,
        override_jumpedia_rank: JumpediaRank | None = None,
    ) -> JumpediaUserAdapter:
        jumpedia_user = self._s.get_or_create_jumpedia_user(
            user.id,
            user.name,
            override_jumpedia_rank or JumpediaRank.DEFAULT,
            True,
            override_jumpedia_rank is not None,
        )

        return JumpediaUserAdapter(jumpedia_user, self)