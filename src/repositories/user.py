from db.models import UserModel
from domain.entities.user import UserEntity
from domain.enums.rank import MetaRank
from domain.errors import business
from domain.typing.user import UserID
from domain.value_objects.string import RealStr
from domain.value_objects.user import UserNameStr
from repositories.dtos.user import UserInsert

from .base import BaseRepository


def user_model_to_entity(model: UserModel) -> UserEntity:
    return UserEntity(
        user_id=model.user_id,
        name=UserNameStr._create_from_real_and_norm(
            RealStr(model.raw_name), model.norm_name
        ),
        rank=MetaRank(model.power),
    )


class UserRepository(BaseRepository):
    def get_by_id(self, user_id: UserID) -> UserEntity | None:
        obj = self._session.get(UserModel, user_id)
        return None if obj is None else user_model_to_entity(obj)

    def create(self, user: UserInsert) -> UserEntity:
        obj = UserModel(
            user_id=user.id,
            norm_name=user.name.norm,
            raw_name=user.name.raw,
            power=user.rank,
        )

        self._session.add(obj)
        self._session.flush()

        return user_model_to_entity(obj)

    def update(
        self,
        user: UserEntity,
    ) -> UserEntity:
        obj = self._session.get(UserModel, user.user_id)

        if obj is None:
            raise business.InternalError("Tried updating a non existant user")

        obj.raw_name = user.name.raw
        obj.norm_name = user.name.norm
        obj.power = user.meta_rank

        return user_model_to_entity(obj)
