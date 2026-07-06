from dataclasses import dataclass

from domain.entities.community import CommunityEntity
from domain.entities.member import MemberEntity
from domain.enums.rank import CommunityRank
from domain.sentinels.default import DEFAULT
from domain.value_objects.community import CommunityNameStr
from repositories.dtos.member import MemberInsert
from repositories.dtos.user import UserInsert
from repositories.member import MemberRepository
from services.community import CommunityAccessService
from services.contexts.interacting_user import InteractingUserContext
from services.dtos.user import UserRef
from services.permission import PermissionService
from services.user import UserExistenceService


@dataclass(frozen=True, slots=True, eq=False)
class MemberService:
    _permission_service: PermissionService
    _member_repo: MemberRepository
    _member_existence_service: MemberExistenceService
    _member_access_service: MemberAccessService
    _user_existence_service: UserExistenceService

    def set_community_rank(
        self,
        user: UserRef,
        community_rank: CommunityRank,
    ) -> MemberEntity:
        community, actor_member = self._member_access_service.get_convenient(DEFAULT)

        target_member = self._member_existence_service.get_or_create(
            MemberInsert(
                self._user_existence_service.get_or_create(
                    UserInsert(user.id, user.name)
                ),
                community.community_id,
            )
        )

        self._permission_service.ensure_actor_member_can_set_community_rank_for_target_member(
            actor_member=actor_member,
            target_member=target_member,
            community_rank=community_rank,
        )

        target_member.community_rank = community_rank

        self._member_repo.update(target_member)

        return target_member


@dataclass(frozen=True, slots=True, eq=False)
class MemberAccessService:
    _ctx: InteractingUserContext
    _member_repo: MemberRepository
    _member_existence_service: MemberExistenceService
    _community_access_service: CommunityAccessService
    _user_existence_service: UserExistenceService
    _permission_service: PermissionService

    def get_target_member_if_actor_member_is_permitted_to_act_for_others(
        self, actor_member: MemberEntity, target_user: UserRef | DEFAULT
    ) -> MemberEntity:
        # Target user is actor
        if target_user is DEFAULT or target_user.id == actor_member.user.user_id:
            return actor_member

        # Awlays create users eagerly
        user = self._user_existence_service.get_or_create(
            UserInsert(target_user.id, target_user.name)
        )

        self._permission_service.ensure_member_can_act_for_other_members(
            actor_member=actor_member
        )

        return self._member_existence_service.get_or_create(
            MemberInsert(
                user,
                actor_member.community_id,
            )
        )

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
        self, community_name: CommunityNameStr | DEFAULT
    ) -> tuple[CommunityEntity, MemberEntity]:
        community = self._community_access_service.get_convenient(community_name)
        member = self.get_or_create_current_with_defaults(community)

        return (community, member)


@dataclass(frozen=True, slots=True, eq=False)
class MemberExistenceService:
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
