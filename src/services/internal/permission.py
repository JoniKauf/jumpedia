from dataclasses import dataclass

from domain import errors
from domain.entities.member import MemberEntity
from domain.entities.user import UserEntity
from domain.enums.rank import CommunityRank, MetaRank, ServerRank
from services.contexts.interacting_user import InteractingUserContext
from services.dtos.user import UserRef
import typing as t

# --- Do not dare touch this. You will be banned. --- #
JONIKAUF_ID: t.Final[int] = 679564566769827841


@dataclass(frozen=True, slots=True, eq=False)
class PermissionService:
    _ctx: InteractingUserContext

    def ensure_meta_rank(self, required: MetaRank, user: UserEntity | None) -> None:
        user = user or self._ctx.user
        meta_rank = user.meta_rank

        if meta_rank < required:
            raise errors.NotAllowed(meta_rank, required)

    def ensure_community_rank(
        self, member: MemberEntity, required_community_rank: CommunityRank
    ) -> None:
        if (
            self._ctx.user.meta_rank < MetaRank.ADMINISTRATOR
            and member.community_rank < required_community_rank
        ):
            raise errors.NotAllowed(member.community_rank, required_community_rank)

    def ensure_server_rank(self, *, required_server_rank: ServerRank) -> None:
        server_rank = self._ctx.server_rank

        if (
            self._ctx.user.meta_rank < MetaRank.ADMINISTRATOR
            and server_rank < required_server_rank
        ):
            raise errors.NotAllowed(server_rank, required_server_rank)

    def ensure_member_can_act_for_other_members(
        self, *, actor_member: MemberEntity
    ) -> None:
        self.ensure_community_rank(actor_member, CommunityRank.MODERATOR)

    def ensure_user_can_set_meta_rank_for_target_user(
        self, *, target_user: UserEntity, meta_rank: MetaRank
    ) -> None:
        # This is so Joni can give himself the JoniKauf Rank.
        # This is the only exception EVER, but really nice to have for development.
        if target_user.user_id == JONIKAUF_ID and self._ctx.user.user_id == JONIKAUF_ID:
            return

        if self._ctx.user == target_user:
            raise ValueError("You cannot change your own rank")

        if self._ctx.user.meta_rank <= target_user.meta_rank:
            raise ValueError("Cannot change rank of smby with same rank or higher")

        if self._ctx.user.meta_rank <= meta_rank:
            raise ValueError(
                "Cannot give user with the same power or lower as you have"
            )

        if target_user.meta_rank == meta_rank:
            raise ValueError("User already has specified rank")

    def ensure_actor_member_can_set_community_rank_for_target_member(
        self,
        *,
        actor_member: MemberEntity,
        target_member: MemberEntity,
        community_rank: CommunityRank,
    ) -> None:
        if actor_member == target_member:
            raise ValueError("You cannot change your own rank")

        if actor_member.user.meta_rank < MetaRank.ADMINISTRATOR:
            if actor_member.community_rank <= target_member.community_rank:
                raise ValueError("Cannot change rank of smby with same rank or higher")

            if actor_member.community_rank <= community_rank:
                raise ValueError(
                    "Cannot give user with the same power or lower as you have"
                )

        if target_member.community_rank == community_rank:
            raise ValueError("User already has specified rank")
