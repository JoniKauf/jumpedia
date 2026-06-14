from dataclasses import dataclass

from domain.entities.user import UserEntity
from repositories.dtos.user import CreateUserDTO
from repositories.user import UserRepository


@dataclass(frozen=True, slots=True, eq=False)
class UserService:
    _repo: UserRepository

    def get_or_create(
        self,
        user: CreateUserDTO,
        *,
        overwrite_name: bool = True,
        overwrite_rank: bool = False,
    ) -> UserEntity:
        existing = self._repo.get_by_id(user.id)

        if existing is None:
            return self._repo.create(user)

        overwrite_any: bool = False

        if overwrite_name:
            existing.name = user.name
            overwrite_any = True

        if overwrite_rank:
            existing.meta_rank = user.rank
            overwrite_any = True

        if not overwrite_any:
            return existing

        return self._repo.update(existing)

