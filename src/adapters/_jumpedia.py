import typing as t

from structures.community import Community, CommunityLimits
from structures.errors import (
    ServerAlreadyConnectedToCommunityError,
    ServerNotConnectedToACommunityError,
    SynsAlreadyTakenError,
)
from structures.jumpedia import Jumpedia
from utils import orm, text
from utils.rank import JumpediaRank

from . import BaseStructureAdapter, errors
from ._community import CommunityAdapter
from ._user import JumpediaUserAdapter, UserAdapter

if t.TYPE_CHECKING:
    from .interaction import InteractionAdapter


def _require_community_with_name(
    c: orm.Cursor, name: text.NormStr, jumpedia_s: Jumpedia
) -> Community:
    community = jumpedia_s.get_community_by_name(c, name)

    if community is None:
        raise errors.StructureNotFoundViaSyn(name, Community, only_name=True)

    return community


class JumpediaAdapter(BaseStructureAdapter[Jumpedia]):
    interaction: InteractionAdapter

    @property
    def _c(self) -> orm.Cursor:
        return self.interaction._c

    # --- Community ---

    def get_communities(self) -> list[CommunityAdapter]:
        return [CommunityAdapter(c, self) for c in self._o.get_communities(self._c)]

    def get_community(self, name: str) -> CommunityAdapter:
        return CommunityAdapter(
            _require_community_with_name(self._c, text.NormStr(name), self._o), self
        )

    def create_community(
        self, name: str, initial_list_name: str | None
    ) -> CommunityAdapter:
        jumpedia_user = self.get_or_create_jumpedia_user(self.interaction.current_user)

        try:
            comm = self._o.create_community(
                self._c, 
                name=text.RealStr(name),
                server_id=self.interaction.current_server.id,
                creator=jumpedia_user._o,
                limits=CommunityLimits(),
            )
        except ServerAlreadyConnectedToCommunityError as e:
            raise errors.ServerAlreadyConnectedToACommunity(e)
        except SynsAlreadyTakenError as e:
            raise errors.SynsAlreadyTaken(e)

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
        community = _require_community_with_name(self._c, text.NormStr(name), self._o)
        self._o.delete_community(self._c, community.id)

    def delete_current_community(self) -> None:
        from discord_.utils_ import shortcuts

        self._o.delete_community(
            self._c, shortcuts.get_current_community(self.interaction).id
        )

    def add_community_to_current_server(self, name: str) -> CommunityAdapter:
        try:
            return CommunityAdapter(
                self._o.add_community_to_server(
                    self._c,
                    self.get_community(name)._o.id,
                    self.interaction.current_server.id,
                ),
                self,
            )
        except ServerAlreadyConnectedToCommunityError as e:
            raise errors.ServerAlreadyConnectedToACommunity(e)

    def remove_community_from_current_server(self) -> CommunityAdapter:
        try:
            community = self._o.remove_community_from_server(
                self._c, self.interaction.current_server._o.id
            )
        except ServerNotConnectedToACommunityError:
            raise errors.ServerNotConnectedToACommunity()

        return CommunityAdapter(community, self)

    # --- Jumpedia User ---

    def get_or_create_jumpedia_user(
        self,
        user: UserAdapter,
        *,
        override_jumpedia_rank: JumpediaRank | None = None,
    ) -> JumpediaUserAdapter:
        jumpedia_user = self._o.get_or_create_jumpedia_user(
            self._c,
            user.id,
            user.name,
            override_jumpedia_rank or JumpediaRank.DEFAULT,
            True,
            override_jumpedia_rank is not None,
        )

        return JumpediaUserAdapter(jumpedia_user, self)
