from sqlalchemy.orm import Session

from domain.entities.user import CommunityUserEntity, UserEntity
from repositories.dtos.user import CreateCommunityUserDTO, CreateUserDTO
from repositories.user import CommunityUserRepository, UserRepository


class UserService:
    def __init__(self, session: Session):
        self._user_repo = UserRepository(session)

    def _get_or_create(
        self,
        user: CreateUserDTO,
        *,
        overwrite_name: bool = True,
        overwrite_rank: bool = False,
    ) -> UserEntity:
        existing = self._user_repo.get_by_id(user.id)

        if existing is None:
            return self._user_repo.create(user)

        overwrite_any: bool = False

        if overwrite_name:
            existing.name = user.name
            overwrite_any = True

        if overwrite_rank:
            existing.meta_rank = user.rank
            overwrite_any = True

        if not overwrite_any:
            return existing

        return self._user_repo.update(existing)


class CommunityUserService:
    def __init__(self, session: Session):
        self._community_user_repo = CommunityUserRepository(session)
        self._user_service = UserService(session)

    def _get_or_create(
        self,
        community_user: CreateCommunityUserDTO,
        *,
        overwrite_rank: bool = False,
        overwrite_selected_list: bool = False,
    ) -> CommunityUserEntity:
        self._user_service._get_or_create(CreateUserDTO(community_user.user.id, community_user.user.name, community_user.user.meta_rank))

        existing = self._community_user_repo.get_by_user_and_community_id(
            community_user.user, community_user.community_id
        )

        if existing is None:
            return self._community_user_repo.create(community_user)

        overwrite_any: bool = False

        if overwrite_rank:
            existing.community_rank = community_user.rank
            overwrite_any = True

        if overwrite_selected_list:
            existing.selected_list_id = community_user.selected_list_id
            overwrite_any = True

        if not overwrite_any:
            return existing

        return self._community_user_repo.update(existing)
