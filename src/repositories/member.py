import types as ts
import typing as t

from sqlalchemy import func, select

from db.models import MemberModel, UserModel
from domain.entities.member import MemberEntity
from domain.entities.user import UserEntity
from domain.enums.rank import CommunityRank
from domain.errors import business
from domain.typing.community import CommunityID
from domain.typing.member import MemberID
from repositories import user
from repositories.base import BaseRepository
from repositories.dtos.member import MemberInsert


def member_model_to_entity(model: MemberModel, user: UserEntity) -> MemberEntity:
    return MemberEntity(
        member_id=model.member_id,
        user=user,
        community_id=model.community_id,
        rank=CommunityRank(model.power),
        selected_list_id=model.selected_list_id,
    )


class MemberRepository(BaseRepository):
    def get_by_member_id(self, member_id: MemberID) -> MemberEntity | None:
        stmt = (
            select(MemberModel, UserModel)
            .join(UserModel, MemberModel.user_id == UserModel.user_id)
            .where(MemberModel.member_id == member_id)
        )

        row = self._session.execute(stmt).one_or_none()

        if row is None:
            return None

        member_obj, user_obj = row.tuple()

        return member_model_to_entity(member_obj, user.user_model_to_entity(user_obj))

    def get_by_user_and_community_id(
        self, user: UserEntity, community_id: CommunityID
    ) -> MemberEntity | None:
        stmt = select(MemberModel).where(
            MemberModel.user_id == user.user_id,
            MemberModel.community_id == community_id,
        )
        obj = self._session.scalar(stmt)
        return None if obj is None else member_model_to_entity(obj, user)

    def create(self, member: MemberInsert) -> MemberEntity:
        obj = MemberModel(
            user_id=member.user.user_id,
            community_id=member.community_id,
            power=member.rank,
            selected_list_id=member.selected_list_id,
        )

        self._session.add(obj)
        self._session.flush()

        return member_model_to_entity(obj, member.user)

    def update(
        self,
        member: MemberEntity,
    ) -> MemberEntity:
        obj = self._session.get(MemberModel, member.member_id)

        if obj is None:
            raise business.InternalError("Tried updating a non existant member")

        obj.power = member.community_rank.value
        obj.selected_list_id = member.selected_list_id

        return member_model_to_entity(obj, member.user)

    def count_grouped_by_community_id(self) -> frozendict[CommunityID, int]:
        stmt = select(MemberModel.community_id, func.count()).group_by(
            MemberModel.community_id
        )

        return frozendict(
            {community_id: count for community_id, count in self._session.execute(stmt)}
        )

    def get_all_by_community_id(self, community_id: int) -> tuple[MemberEntity, ...]:
        stmt = (
            select(MemberModel, UserModel)
            .join(UserModel, UserModel.user_id == MemberModel.user_id)
            .where(MemberModel.community_id == community_id)
        )

        return tuple(
            member_model_to_entity(
                member,
                user.user_model_to_entity(usr),
            )
            for member, usr in self._session.execute(stmt)
        )

    def count_by_community_id(self, community_id: int) -> int:
        stmt = (
            select(func.count())
            .select_from(MemberModel)
            .where(MemberModel.community_id == community_id)
        )
        return self._session.scalar(stmt) or 0
