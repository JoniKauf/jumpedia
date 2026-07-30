import types as ts

from sqlalchemy import func, select

from db.models import ListModel as ListModel
from domain.entities.list import ListEntity
from domain.errors import business
from domain.errors.internal import NotFoundById
from domain.typing.community import CommunityID
from domain.typing.list import ListID
from domain.value_objects.list import ListNameStr
from repositories.dtos.list import ListInsert

from .base import BaseRepository


def list_model_to_entity(model: ListModel) -> ListEntity:
    return ListEntity(
        key=(model.list_id,),
        community_id=model.community_id,
        name=ListNameStr._create_from_real_and_norm(model.real_name, model.norm_name),
    )


class ListRepository(BaseRepository):
    def create(self, list: ListInsert) -> ListEntity:
        obj = ListModel(
            community_id=list.community_id,
            norm_name=list.name.hash,
            real_name=list.name.real,
        )

        self._session.add(obj)
        self._session.flush()

        return list_model_to_entity(obj)

    def get_by_id(self, list_id: ListID) -> ListEntity | None:
        obj = self._session.get(ListModel, list_id)
        return None if obj is None else list_model_to_entity(obj)

    def get_by_community_and_name(
        self, community_id: CommunityID, name: ListNameStr
    ) -> ListEntity | None:
        stmt = select(ListModel).where(
            ListModel.community_id == community_id,
            ListModel.norm_name == name.hash,
        )
        obj = self._session.scalar(stmt)
        return None if obj is None else list_model_to_entity(obj)

    def get_all_by_community(self, community_id: CommunityID) -> tuple[ListEntity, ...]:
        stmt = select(ListModel).where(ListModel.community_id == community_id)
        return tuple(
            list_model_to_entity(obj) for obj in self._session.scalars(stmt).all()
        )

    def count_by_community(self, community_id: CommunityID) -> int:
        stmt = (
            select(func.count())
            .select_from(ListModel)
            .where(ListModel.community_id == community_id)
        )
        return self._session.scalar(stmt) or 0

    def count_grouped_by_community_id(self) -> frozendict[CommunityID, int]:
        stmt = select(ListModel.community_id, func.count()).group_by(
            ListModel.community_id
        )

        return frozendict(
            {
                CommunityID(community_id): count
                for community_id, count in self._session.execute(stmt)
            }
        )

    def delete(self, list_id: ListID) -> None:
        obj = self._session.get(ListModel, list_id)

        if obj is None:
            raise NotFoundById(ListEntity, list_id)

        self._session.delete(obj)
        self._session.flush()

    def update(self, list: ListEntity) -> None:
        obj = self._session.get(ListModel, list.list_id)

        if obj is None:
            raise NotFoundById(ListEntity, list.list_id)

        obj.norm_name = list.name.hash
        obj.real_name = list.name.real

        self._session.flush()
