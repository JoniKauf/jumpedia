from db.models import User
from domain.entities.user import UserEntity
from domain.enums.rank import MetaRank
from domain.types.user import UserID
from domain.value_objects.string import RealStr
from domain.value_objects.user import UserName
from repositories.dtos.user import CreateUserDTO

from .base import BaseRepository


def _user_model_to_entity(model: User) -> UserEntity:
    return UserEntity(
        id=model.user_id,
        name=UserName(_real=RealStr(model.raw_name), _norm=model.norm_name),
        rank=MetaRank(model.power),
    )


class UserRepository(BaseRepository):
    def get_by_id(self, user_id: UserID) -> UserEntity | None:
        obj = self.session.get(User, user_id)
        return None if obj is None else _user_model_to_entity(obj)

    def create(self, user: CreateUserDTO) -> UserEntity:
        obj = User(
            user_id=user.id,
            norm_name=user.name.norm,
            raw_name=user.name.raw,
            power=user.rank.value,
        )

        self.session.add(obj)
        self.session.flush()

        return _user_model_to_entity(obj)

    def update(
        self,
        user: UserEntity,
    ) -> UserEntity:
        obj = self.session.get(User, user.id)

        if obj is None:
            raise RuntimeError("Tried updating a non existant user")

        obj.raw_name = user.name.raw
        obj.norm_name = user.name.norm
        obj.power = user.meta_rank.value

        return _user_model_to_entity(obj)
