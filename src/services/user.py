from dataclasses import dataclass

from domain.entities.user import UserEntity
from domain.enums.rank import MetaRank
from repositories.dtos.user import UserInsert
from repositories.user import UserRepository
from services.contexts.interacting_user import InteractingUserContext
from services.dtos.user import UserRef
from services.internal.permission import PermissionService


@dataclass(frozen=True, slots=True, eq=False)
class UserService:
    _ctx: InteractingUserContext
    _permission_service: PermissionService
    _user_repo: UserRepository
    _user_existence_server: UserExistenceService

    def set_meta_rank(self, user: UserRef, meta_rank: MetaRank) -> UserEntity:
        target_user = self._user_existence_server.get_or_create(
            UserInsert(user.id, user.name)
        )

        self._permission_service.ensure_user_can_set_meta_rank_for_target_user(
            target_user=target_user, meta_rank=meta_rank
        )

        target_user.meta_rank = meta_rank

        self._user_repo.update(target_user)

        return target_user

@dataclass(frozen=True, slots=True, eq=False)
class UserExistenceService:
    _user_repo: UserRepository

    def get_or_create(
        self,
        user: UserInsert,
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
