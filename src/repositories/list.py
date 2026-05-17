from sqlalchemy import select, func, delete

from db.models import List as List, Task
from domain.entities.list import ListEntity
from domain.value_objects.string import StrStore
from .base import BaseRepository


def _list_model_to_entity(model: List) -> ListEntity:
    return ListEntity(
        id=model.list_id,
        community_id=model.community_id,
        name=StrStore(_real=model.real_name, _norm=model.norm_name),
    )


class ListRepository(BaseRepository):
    def create(self, community_id: int, name: StrStore) -> ListEntity:
        obj = List(
            community_id=community_id,
            norm_name=name.norm,
            real_name=name.real,
        )

        self.session.add(obj)
        self.session.flush()

        return _list_model_to_entity(obj)

    def get_by_id(self, list_id: int) -> ListEntity | None:
        obj = self.session.get(List, list_id)
        return None if obj is None else _list_model_to_entity(obj)

    def get_by_name(self, community_id: int, name: StrStore) -> ListEntity | None:
        stmt = select(List).where(
            List.community_id == community_id,
            List.norm_name == name.norm,
        )
        obj = self.session.scalar(stmt)
        return None if obj is None else _list_model_to_entity(obj)

    def get_all(self, community_id: int) -> list[ListEntity]:
        stmt = select(List).where(List.community_id == community_id)
        return [_list_model_to_entity(obj) for obj in self.session.scalars(stmt).all()]

    def count(self, community_id: int) -> int:
        stmt = (
            select(func.count())
            .select_from(List)
            .where(List.community_id == community_id)
        )
        return self.session.scalar(stmt) or 0

    def delete(self, list_id: int) -> None:
        obj = self.session.get(List, list_id)
        if obj:
            self.session.delete(obj)
            self.session.flush()

    def count_tasks(self, list_id: int) -> int:
        stmt = select(func.count()).select_from(Task).where(Task.list_id == list_id)
        return self.session.scalar(stmt) or 0
