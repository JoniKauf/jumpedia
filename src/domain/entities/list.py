from domain.entities.base import BaseEntity

lazy from domain.typing.community import CommunityID
from domain.typing.list import ListID

lazy from domain.value_objects.list import ListNameStr


class ListEntity(BaseEntity[ListID]):
    def __init__(
        self, list_id: ListID, community_id: CommunityID, name: ListNameStr
    ) -> None:
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
    def name(self) -> ListNameStr:
        return self._name

    @name.setter
    def name(self, value: ListNameStr) -> None:
        self._name = value
