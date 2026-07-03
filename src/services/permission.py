from dataclasses import dataclass

from domain import errors
from domain.entities.member import MemberEntity
from domain.entities.user import UserEntity
from domain.enums.rank import CommunityRank, MetaRank, ServerRank
from services.contexts.interacting_user import InteractingUserContext


@dataclass(frozen=True, slots=True, eq=False)
class PermissionService:
    _ctx: InteractingUserContext

    def ensure_meta_rank(self, required: MetaRank, user: UserEntity | None) -> None:
        user = user or self._ctx.user
        meta_rank = user.meta_rank

        if meta_rank.value < required.value:
            raise errors.NotAllowed(meta_rank, required)

    def ensure_community_rank(
        self, member: MemberEntity, required: CommunityRank
    ) -> None:
        if (
            not self._ctx.user.meta_rank.value < MetaRank.ADMINISTRATOR
            and member.community_rank.value < required.value
        ):
            raise errors.NotAllowed(member.community_rank, required)

    def ensure_server_rank(self, required: ServerRank) -> None:
        server_rank = self._ctx.server_rank

        if not self._ctx.user.meta_rank.value < MetaRank.ADMINISTRATOR and server_rank.value < required.value:
            raise errors.NotAllowed(server_rank, required)
        
    def ensure_member_can_act_for_others(self, actor_member: MemberEntity) -> None:
        self.ensure_community_rank(actor_member, CommunityRank.MODERATOR)