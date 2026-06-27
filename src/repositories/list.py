from sqlalchemy import func, select

from db.models import ListModel as ListModel
from domain import errors
from domain.entities.list import ListEntity
from domain.types.community import CommunityID
from domain.types.list import ListID
from domain.value_objects.list import ListName
from repositories.dtos.list import ListInsert

from .base import BaseRepository


def list_model_to_entity(model: ListModel) -> ListEntity:
    return ListEntity(
        list_id=model.list_id,
        community_id=model.community_id,
        name=ListName(_real=model.real_name, _norm=model.norm_name),
    )


class ListRepository(BaseRepository):
    def create(self, list: ListInsert) -> ListEntity:
        obj = ListModel(
            community_id=list.community_id,
            norm_name=list.name.norm,
            real_name=list.name.real,
        )

        self.session.add(obj)
        self.session.flush()

        return list_model_to_entity(obj)

    def get_by_id(self, list_id: ListID) -> ListEntity | None:
        obj = self.session.get(ListModel, list_id)
        return None if obj is None else list_model_to_entity(obj)

    def get_by_community_and_name(
        self, community_id: CommunityID, name: ListName
    ) -> ListEntity | None:
        stmt = select(ListModel).where(
            ListModel.community_id == community_id,
            ListModel.norm_name == name.norm,
        )
        obj = self.session.scalar(stmt)
        return None if obj is None else list_model_to_entity(obj)

    def get_all_by_community(self, community_id: CommunityID) -> list[ListEntity]:
        stmt = select(ListModel).where(ListModel.community_id == community_id)
        return [list_model_to_entity(obj) for obj in self.session.scalars(stmt).all()]

    def count_by_community(self, community_id: CommunityID) -> int:
        stmt = (
            select(func.count())
            .select_from(ListModel)
            .where(ListModel.community_id == community_id)
        )
        return self.session.scalar(stmt) or 0

    def count_grouped_by_community_id(self) -> dict[CommunityID, int]:
        stmt = select(ListModel.community_id, func.count()).group_by(ListModel.community_id)

        return {
            CommunityID(community_id): count
            for community_id, count in self.session.execute(stmt)
        }

    def delete(self, list_id: ListID) -> None:
        obj = self.session.get(ListModel, list_id)

        if obj is None:
            raise errors.NotFoundById(ListEntity)

        self.session.delete(obj)
        self.session.flush()

    def update(self, list: ListEntity) -> None:
        obj = self.session.get(ListModel, list.primary_key)

        if obj is None:
            raise errors.NotFoundById(ListEntity)

        obj.norm_name = list.name.norm
        obj.real_name = list.name.real

        self.session.flush()
