from dataclasses import dataclass

from domain.entities.community import CommunityEntity
from domain.entities.list import ListEntity
from domain.entities.member import MemberEntity
from domain.enums.rank import CommunityRank, MetaRank, ServerRank
from domain.sentinels.default import DEFAULT
from domain.sentinels.unknown import UNKNOWN
from domain.typing.community import CommunityID
from domain.value_objects.community import CommunityNameStr
from repositories.community import CommunityRepository
from repositories.dtos.member import MemberInsert
from repositories.dtos.user import UserInsert
from repositories.list import ListRepository

lazy from repositories.member import MemberRepository
lazy from services.community import CommunityAccessService
lazy from services.contexts.interacting_user import InteractingUserContext
from services.dtos.member import MemberInfo, UserAndMemberInfo
from services.dtos.user import UserRef

lazy from services.internal.permission import PermissionService
lazy from services.user import UserAccessService, UserExistenceService


@dataclass(frozen=True, slots=True, eq=False)
class MemberService:
    _member_repository: MemberRepository

    _member_access_service: MemberAccessService
    _member_existence_service: MemberExistenceService
    _permission_service: PermissionService
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

        self._member_repository.update(target_member)

        return target_member


@dataclass(frozen=True, slots=True, eq=False)
class MemberQueryService:
    _ctx: InteractingUserContext

    _community_repository: CommunityRepository
    _list_repository: ListRepository

    _member_existence_service: MemberExistenceService
    _user_access_service: UserAccessService

    def get_info(self, user: UserRef | DEFAULT) -> UserAndMemberInfo:
        user_entity = self._user_access_service.get_or_create_with_user_ref(user)

        del user

        meta_rank: MetaRank = user_entity.meta_rank
        server_rank: ServerRank | UNKNOWN = UNKNOWN
        member_info: MemberInfo | None = None

        community = self._community_repository.get_by_server_id(self._ctx.server_id)

        if community is not None:
            member = self._member_existence_service.get_or_create(
                MemberInsert(user_entity, community.community_id)
            )

            selected_list = (
                None
                if member.selected_list_id is None
                else self._list_repository.get_by_id(member.selected_list_id)
            )
            member_info = MemberInfo(member.community_rank, selected_list)

        return UserAndMemberInfo(
            user_entity.user_id,
            user_entity.name,
            server_rank,
            meta_rank,
            member_info,
        )


@dataclass(frozen=True, slots=True, eq=False)
class MemberAccessService:
    _ctx: InteractingUserContext

    _member_repository: MemberRepository

    _community_access_service: CommunityAccessService
    _member_existence_service: MemberExistenceService
    _permission_service: PermissionService
    _user_access_service: UserAccessService
    _user_existence_service: UserExistenceService

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
        return self._member_repository.create(
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

    def get_or_create_with_user_ref(
        self, user: UserRef | DEFAULT, community_id: CommunityID
    ) -> MemberEntity:
        return self._member_existence_service.get_or_create(
            MemberInsert(
                self._user_access_service.get_or_create_with_user_ref(user),
                community_id,
            )
        )


@dataclass(frozen=True, slots=True, eq=False)
class MemberExistenceService:
    _member_repository: MemberRepository

    _user_existence_service: UserExistenceService

    def get_or_create(
        self,
        member: MemberInsert,
        *,
        overwrite_rank: bool = False,
        overwrite_selected_list: bool = False,
    ) -> MemberEntity:
        existing = self._member_repository.get_by_user_and_community_id(
            member.user, member.community_id
        )

        if existing is None:
            return self._member_repository.create(member)

        overwrite_any: bool = False

        if overwrite_rank:
            existing.community_rank = member.rank
            overwrite_any = True

        if overwrite_selected_list:
            existing.selected_list_id = member.selected_list_id
            overwrite_any = True

        if not overwrite_any:
            return existing

        return self._member_repository.update(existing)
