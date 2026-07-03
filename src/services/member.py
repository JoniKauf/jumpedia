from dataclasses import dataclass

from domain.entities.community import CommunityEntity
from domain.entities.member import MemberEntity
from domain.value_objects.community import CommunityNameStr
from repositories.member import MemberRepository
from repositories.dtos.member import MemberInsert
from services.community import CommunityAccessService
from services.contexts.interacting_user import InteractingUserContext
from services.user import UserService


@dataclass(frozen=True, slots=True, eq=False)
class MemberService:
    _member_repo: MemberRepository

    def get_or_create(
        self,
        member: MemberInsert,
        *,
        overwrite_rank: bool = False,
        overwrite_selected_list: bool = False,
    ) -> MemberEntity:
        existing = self._member_repo.get_by_user_and_community_id(
            member.user, member.community_id
        )

        if existing is None:
            return self._member_repo.create(member)

        overwrite_any: bool = False

        if overwrite_rank:
            existing.community_rank = member.rank
            overwrite_any = True

        if overwrite_selected_list:
            existing.selected_list_id = member.selected_list_id
            overwrite_any = True

        if not overwrite_any:
            return existing

        return self._member_repo.update(existing)


@dataclass(frozen=True, slots=True, eq=False)
class MemberAccessService:
    _ctx: InteractingUserContext
    _member_repo: MemberRepository
    _community_access_service: CommunityAccessService

    def get_or_create_current_with_defaults(
        self, community: CommunityEntity
    ) -> MemberEntity:
        return self._member_repo.create(
            MemberInsert(
                self._ctx.user,
                community.community_id,
            )
        )

    def get_convenient(
        self, community_name: CommunityNameStr | None
    ) -> tuple[CommunityEntity, MemberEntity]:
        community = self._community_access_service.get_convenient(community_name)
        member = self.get_or_create_current_with_defaults(community)

        return (community, member)
