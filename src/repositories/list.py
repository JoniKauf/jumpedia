from sqlalchemy import func, select

from db.models import List as List
from domain import errors
from domain.entities.list import ListEntity
from domain.types.community import CommunityID
from domain.types.list import ListID
from domain.value_objects.list import ListName
from repositories.dtos.list import CreateListDTO

from .base import BaseRepository


def _list_model_to_entity(model: List) -> ListEntity:
    return ListEntity(
        id=model.list_id,
        community_id=model.community_id,
        name=ListName(_real=model.real_name, _norm=model.norm_name),
    )


class ListRepository(BaseRepository):
    def create(self, list: CreateListDTO) -> ListEntity:
        obj = List(
            community_id=list.community_id,
            norm_name=list.name.norm,
            real_name=list.name.real,
        )

        self.session.add(obj)
        self.session.flush()

        return _list_model_to_entity(obj)

    def get_by_id(self, list_id: ListID) -> ListEntity | None:
        obj = self.session.get(List, list_id)
        return None if obj is None else _list_model_to_entity(obj)

    def get_by_community_and_name(
        self, community_id: CommunityID, name: ListName
    ) -> ListEntity | None:
        stmt = select(List).where(
            List.community_id == community_id,
            List.norm_name == name.norm,
        )
        obj = self.session.scalar(stmt)
        return None if obj is None else _list_model_to_entity(obj)

    def get_all_by_community(self, community_id: CommunityID) -> list[ListEntity]:
        stmt = select(List).where(List.community_id == community_id)
        return [_list_model_to_entity(obj) for obj in self.session.scalars(stmt).all()]

    def count_by_community(self, community_id: CommunityID) -> int:
        stmt = (
            select(func.count())
            .select_from(List)
            .where(List.community_id == community_id)
        )
        return self.session.scalar(stmt) or 0

    def count_grouped_by_community_id(self) -> dict[CommunityID, int]:
        stmt = select(List.community_id, func.count()).group_by(List.community_id)

        return {
            CommunityID(community_id): count
            for community_id, count in self.session.execute(stmt)
        }

    def delete(self, list_id: ListID) -> None:
        obj = self.session.get(List, list_id)

        if obj is None:
            raise errors.NotFoundById(ListEntity)

        self.session.delete(obj)
        self.session.flush()

    def update(self, list: ListEntity) -> None:
        obj = self.session.get(List, list.id)

        if obj is None:
            raise errors.NotFoundById(ListEntity)

        obj.norm_name = list.name.norm
        obj.real_name = list.name.real

        self.session.flush()
