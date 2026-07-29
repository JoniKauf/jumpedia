from dataclasses import dataclass

from domain.entities.user import UserEntity
from domain.enums.rank import MetaRank
from domain.sentinels.default import DEFAULT
from repositories.dtos.user import UserInsert

lazy from repositories.user import UserRepository
lazy from services.contexts.interacting_user import InteractingUserContext
from services.dtos.user import MetaRankEdited, UserRef

lazy from services.internal.permission import PermissionService


@dataclass(frozen=True, slots=True, eq=False)
class UserService:
    _user_repository: UserRepository

    _permission_service: PermissionService
    _user_existence_server: UserExistenceService

    def edit_meta_rank(self, user: UserRef, meta_rank: MetaRank) -> MetaRankEdited:
        target_user = self._user_existence_server.get_or_create(
            UserInsert(user.id, user.name)
        )

        self._permission_service.ensure_user_can_set_meta_rank_for_target_user(
            target_user=target_user, meta_rank=meta_rank
        )

        updated_user = self._user_repository.update_meta_rank(
            target_user.user_id, meta_rank
        )

        return MetaRankEdited(target_user, updated_user)


@dataclass(frozen=True, slots=True, eq=False)
class UserAccessService:
    _ctx: InteractingUserContext

    _user_existence_service: UserExistenceService

    def get_or_create_with_user_ref(self, user: UserRef | DEFAULT) -> UserEntity:
        return (
            self._ctx.user
            if user is DEFAULT
            else self._user_existence_service.get_or_create(
                UserInsert(user.id, user.name)
            )
        )


@dataclass(frozen=True, slots=True, eq=False)
class UserExistenceService:
    _user_repository: UserRepository

    def get_or_create(
        self,
        user: UserInsert,
        *,
        overwrite_name: bool = True,
        overwrite_rank: bool = False,
    ) -> UserEntity:
        existing = self._user_repository.get_by_id(user.id)

        if existing is None:
            return self._user_repository.create(user)

        if not overwrite_name and not overwrite_rank:
            return existing

        new = UserEntity(
            (user.id,),
            user.name if overwrite_name else existing.name,
            user.meta_rank if overwrite_rank else existing.meta_rank,
        )

        del existing

        return self._user_repository.update(new)
