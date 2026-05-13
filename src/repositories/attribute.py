

from db.models import Attribute
from repositories.base import BaseRepository


class AttributeRepository(BaseRepository):
    def get_by_id(self, attribute_id: int) -> Attribute | None:
        return self.session.get(Attribute, attribute_id)
    
    def get_by_list_id(self, list_id: int) -> list[Attribute]:
        return self.session.query(Attribute).filter(Attribute.list_id == list_id).all()