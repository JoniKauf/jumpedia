from db.models import List as ListORM
from .base import BaseRepository
from utils import text

class ListRepository(BaseRepository):
    def create(self, community_id: int, norm_name: text.NormStr, real_name: text.RealStr) -> ListORM:
        obj = ListORM(
            community_id=community_id,
            norm_name=norm_name,
            real_name=real_name,
        )

        self.session.add(obj)
        self.session.flush()

        return obj

    def get_by_id(self, list_id: int) -> ListORM | None:
        return self.session.get(ListORM, list_id)

    def get_by_name(self, community_id: int, name: str) -> ListORM | None:
        return (
            self.session.query(ListORM)
            .filter(
                ListORM.community_id == community_id,
                ListORM.norm_name == text.NormStr(name),
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