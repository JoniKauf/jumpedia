from dataclasses import dataclass

from domain.entities.community_user import CommunityUserEntity
from domain.enums.rank import CommunityRank, MetaRank, ServerRank
from domain import errors
from services.contexts.interacting_user import InteractingUserContext


@dataclass(frozen=True, slots=True, eq=False)
class PermissionService:
    _ctx: InteractingUserContext

    def ensure_meta_rank(self, required: MetaRank) -> None:
        meta_rank = self._ctx.user.meta_rank

        if meta_rank.value < required.value:
            raise errors.NotAllowed(meta_rank, required)

    def ensure_community_rank(
        self, community_user: CommunityUserEntity, required: CommunityRank
    ) -> None:
        if (
            not self._ctx.user.meta_rank
            and community_user.community_rank.value < required.value
        ):
            raise errors.NotAllowed(community_user.community_rank, required)

    def ensure_server_rank(self, required: ServerRank) -> None:
        server_rank = self._ctx.server_rank

        if not self._ctx.user.meta_rank and server_rank.value < required.value:
            raise errors.NotAllowed(server_rank, required)
