



from dataclasses import dataclass

from domain.entities.community import CommunityEntity
from domain.entities.community_user import CommunityUserEntity
from domain.value_objects.community import CommunityName
from repositories.community_user import CommunityUserRepository
from repositories.dtos.community_user import CreateCommunityUserDTO
from services.community import CommunityAccessService
from services.user import UserService
from services.contexts.interacting_user import InteractingUserContext

@dataclass(frozen=True, slots=True, eq=False)
class CommunityUserService:
    _repo: CommunityUserRepository
    _user_service: UserService

    def get_or_create(
        self,
        community_user: CreateCommunityUserDTO,
        *,
        overwrite_rank: bool = False,
        overwrite_selected_list: bool = False,
    ) -> CommunityUserEntity:
        existing = self._repo.get_by_user_and_community_id(
            community_user.user, community_user.community_id
        )

        if existing is None:
            return self._repo.create(community_user)

        overwrite_any: bool = False

        if overwrite_rank:
            existing.community_rank = community_user.rank
            overwrite_any = True

        if overwrite_selected_list:
            existing.selected_list_id = community_user.selected_list_id
            overwrite_any = True

        if not overwrite_any:
            return existing

        return self._repo.update(existing)


@dataclass(frozen=True, slots=True, eq=False)
class CommunityUserAccessService:
    _ctx: InteractingUserContext
    _repo: CommunityUserRepository
    _community_access_service: CommunityAccessService

    def get_or_create_current_with_defaults(
        self, community: CommunityEntity
    ) -> CommunityUserEntity:
        return self._repo.create(
            CreateCommunityUserDTO(
                self._ctx.user,
                community.id,
            )
        )

    def get_convenient(
        self, community_name: CommunityName | None
    ) -> tuple[CommunityEntity, CommunityUserEntity]:
        community = self._community_access_service.get_convenient(community_name)
        community_user = self.get_or_create_current_with_defaults(community)

        return (community, community_user)
