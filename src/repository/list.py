from db.models import List as ListORM
from domain.value_objects import s
from .base import BaseRepository
from utils import text

class ListRepository(BaseRepository):
    def create(self, community_id: int, name: s.StrStore) -> ListORM:
        obj = ListORM(
            community_id=community_id,
            norm_name=name.norm,
            real_name=name.real,
        )

        self.session.add(obj)
        self.session.flush()

        return obj

    def get_by_id(self, list_id: int) -> ListORM | None:
        return self.session.get(ListORM, list_id)

    def get_by_name(self, community_id: int, name: s.StrStore) -> ListORM | None:
        return (
            self.session.query(ListORM)
            .filter(
                ListORM.community_id == community_id,
                ListORM.norm_name == name.norm,
            )
            .first()
        )

    def get_by_community(self, community_id: int) -> list[ListORM]:
        return (
            self.session.query(ListORM)
            .filter(ListORM.community_id == community_id)
            .all()
        )
    
    def delete(self, list_id: int) -> None:
        obj = self.get_by_id(list_id)
        if obj:
            self.session.delete(obj)