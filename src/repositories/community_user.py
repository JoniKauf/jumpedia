import types as ts

from sqlalchemy import func, select

from db.models import CommunityUserModel, UserModel
from domain import errors
from domain.entities.community_user import CommunityUserEntity
from domain.entities.user import UserEntity
from domain.enums.rank import CommunityRank
from domain.types.community import CommunityID
from repositories import user as user_module
from repositories.base import BaseRepository
from repositories.dtos.community_user import CommunityUserInsert


def _community_user_model_to_entity(
    model: CommunityUserModel, user: UserEntity
) -> CommunityUserEntity:
    return CommunityUserEntity(
        community_user_id=model.community_user_id,
        user=user,
        community_id=model.community_id,
        rank=CommunityRank(model.power),
        selected_list_id=model.selected_list_id,
    )


class CommunityUserRepository(BaseRepository):
    def get_by_user_and_community_id(
        self, user: UserEntity, community_id: CommunityID
    ) -> CommunityUserEntity | None:
        stmt = select(CommunityUserModel).where(
            CommunityUserModel.user_id == user.user_id,
            CommunityUserModel.community_id == community_id,
        )
        obj = self._session.scalar(stmt)
        return None if obj is None else _community_user_model_to_entity(obj, user)

    def create(self, community_user: CommunityUserInsert) -> CommunityUserEntity:
        obj = CommunityUserModel(
            user_id=community_user.user.user_id,
            community_id=community_user.community_id,
            power=community_user.rank.value,
            selected_list_id=community_user.selected_list_id,
        )

        self._session.add(obj)
        self._session.flush()

        return _community_user_model_to_entity(obj, community_user.user)

    def update(
        self,
        community_user: CommunityUserEntity,
    ) -> CommunityUserEntity:
        obj = self._session.get(CommunityUserModel, community_user.community_user_id)

        if obj is None:
            raise errors.InternalError("Tried updating a non existant community user")

        obj.power = community_user.community_rank.value
        obj.selected_list_id = community_user.selected_list_id

        return _community_user_model_to_entity(obj, community_user.user)

    def count_grouped_by_community_id(self) -> ts.MappingProxyType[CommunityID, int]:
        stmt = select(CommunityUserModel.community_id, func.count()).group_by(
            CommunityUserModel.community_id
        )

        return ts.MappingProxyType(
            {community_id: count for community_id, count in self._session.execute(stmt)}
        )

    def get_all_by_community_id(
        self, community_id: int
    ) -> tuple[CommunityUserEntity, ...]:
        stmt = (
            select(CommunityUserModel, UserModel)
            .join(UserModel, UserModel.user_id == CommunityUserModel.user_id)
            .where(CommunityUserModel.community_id == community_id)
        )

        return tuple(
            _community_user_model_to_entity(
                community_user,
                user_module._user_model_to_entity(user),
            )
            for community_user, user in self._session.execute(stmt)
        )

    def count_by_community_id(self, community_id: int) -> int:
        stmt = (
            select(func.count())
            .select_from(CommunityUserModel)
            .where(CommunityUserModel.community_id == community_id)
        )
        return self._session.scalar(stmt) or 0
