from domain.entities.base import BaseEntity
from domain.types.community import CommunityID
from domain.types.list import ListID
from domain.value_objects.list import ListName


class ListEntity(BaseEntity[ListID]):
    def __init__(self, list_id: ListID, community_id: CommunityID, name: ListName) -> None:
        super().__init__(list_id)

        self._community_id = community_id
        self.name = name

    @property
    def list_id(self) -> ListID:
        return self._composite_key[0]
    
    @property
    def community_id(self) -> CommunityID:
        return self._community_id

    @property
    def name(self) -> ListName:
        return self._name

    @name.setter
    def name(self, value: ListName) -> None:
        self._name = value
