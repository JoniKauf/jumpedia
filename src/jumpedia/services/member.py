from dataclasses import dataclass

from jumpedia.domain.entities.community import CommunityEntity
from jumpedia.domain.entities.list import ListEntity
from jumpedia.domain.entities.member import MemberEntity
from jumpedia.domain.entities.user import UserEntity
from jumpedia.domain.enums.rank import CommunityRank, MetaRank, ServerRank
from jumpedia.domain.sentinels.default import DEFAULT
from jumpedia.domain.sentinels.unknown import UNKNOWN
from jumpedia.domain.typing.community import CommunityID
from jumpedia.domain.value_objects.community import CommunityNameStr
from jumpedia.domain.value_objects.list import ListNameStr
from jumpedia.repositories.community import CommunityRepository
from jumpedia.repositories.dtos.member import MemberInsert
from jumpedia.repositories.dtos.user import UserInsert
from jumpedia.repositories.list import ListRepository

lazy from jumpedia.repositories.member import MemberRepository
lazy from jumpedia.services.community import CommunityAccessService
lazy from jumpedia.services.contexts.interacting_user import InteractingUserContext
from jumpedia.services.dtos.member import (
    CommunityRankEdited,
    MemberInfo,
    SelectedListEdited,
    UserAndMemberInfo,
)
from jumpedia.services.dtos.user import UserRef

lazy from jumpedia.services.internal.permission import PermissionService
from jumpedia.services.list import ListAccessService

lazy from jumpedia.services.user import UserAccessService, UserExistenceService


@dataclass(frozen=True, slots=True, eq=False)
class MemberService:
    _member_repository: MemberRepository

    _list_access_service: ListAccessService
    _member_access_service: MemberAccessService
    _member_existence_service: MemberExistenceService
    _permission_service: PermissionService
    _user_existence_service: UserExistenceService

    def edit_community_rank(
        self,
        user: UserRef,
        community_rank: CommunityRank,
    ) -> CommunityRankEdited:
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

        del actor_member

        updated_member = self._member_repository.update_community_rank(
            target_member.member_id, target_member.user, community_rank
        )

        return CommunityRankEdited(target_member, updated_member)

    def edit_selected_list(
        self, list_name: ListNameStr | None, user: UserRef | DEFAULT
    ) -> SelectedListEdited:
        actor_member: MemberEntity
        lst: ListEntity | None

        if list_name is None:
            _, actor_member = self._member_access_service.get_convenient(DEFAULT)
            lst = None
        else:
            _, actor_member, lst = self._list_access_service.get_convenient(
                DEFAULT, list_name
            )

        target_member = self._member_access_service.get_target_member_if_actor_member_is_permitted_to_act_for_others(
            actor_member, user
        )

        del actor_member

        updated_member = self._member_repository.update_selected_list(
            target_member.member_id,
            target_member.user,
            None if lst is None else lst.list_id,
        )

        return SelectedListEdited(target_member, updated_member, lst)


@dataclass(frozen=True, slots=True, eq=False)
class MemberQueryService:
    _ctx: InteractingUserContext

    _community_repository: CommunityRepository
    _list_repository: ListRepository

    _member_existence_service: MemberExistenceService
    _user_access_service: UserAccessService

    def get_user_and_member_info(self, user: UserRef | DEFAULT) -> UserAndMemberInfo:
        user_entity = self._user_access_service.get_or_create_with_user_ref(user)

        del user

        server_rank: ServerRank | UNKNOWN = UNKNOWN
        member_info: MemberInfo | None = None

        community = self._community_repository.get_by_server_id(self._ctx.server_id)

        member_entity: MemberEntity | None = None

        if community is not None:
            member_entity = self._member_existence_service.get_or_create(
                MemberInsert(user_entity, community.community_id)
            )

            selected_list = (
                None
                if member_entity.selected_list_id is None
                else self._list_repository.get_by_id(member_entity.selected_list_id)
            )
            member_info = MemberInfo(member_entity, selected_list)

        return UserAndMemberInfo(
            user_entity,
            server_rank,
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

        # Always create users eagerly
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
        return self._member_existence_service.get_or_create(
            MemberInsert(self._ctx.user, community.community_id)
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

        if not overwrite_rank and not overwrite_selected_list:
            return existing

        new = MemberEntity(
            (existing.member_id,),
            existing.user,
            existing.community_id,
            member.community_rank if overwrite_rank else existing.community_rank,
            (
                member.selected_list_id
                if overwrite_selected_list
                else existing.selected_list_id
            ),
        )

        del existing

        return self._member_repository.update(new)
