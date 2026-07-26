from db.models import UserModel
from domain.entities.user import UserEntity
from domain.enums.rank import MetaRank
from domain.errors import business
from domain.errors.internal import InternalError, NotFoundById
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
        rank=MetaRank(model.rank),
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
            rank=user.rank.value,
        )

        self._session.add(obj)
        self._session.flush()

        return user_model_to_entity(obj)

    def update_meta_rank(self, user_id: UserID, meta_rank: MetaRank) -> UserEntity:
        obj = self._session.get(UserModel, user_id)

        if obj is None:
            raise NotFoundById(UserEntity, user_id)

        obj.rank = meta_rank

        self._session.flush()

        return user_model_to_entity(obj)

    # This should only be used if everything is changed!!
    def update(
        self,
        user: UserEntity,
    ) -> UserEntity:
        obj = self._session.get(UserModel, user.user_id)

        if obj is None:
            raise NotFoundById(UserEntity, user.user_id)

        obj.raw_name = user.name.raw
        obj.norm_name = user.name.norm
        obj.rank = user.meta_rank

        return user_model_to_entity(obj)
