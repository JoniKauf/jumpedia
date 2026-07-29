from domain.entities.base import BaseEntity

lazy from domain.typing.community import CommunityID
from domain.typing.list import ListID

lazy from domain.value_objects.list import ListNameStr
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ListEntity(BaseEntity[ListID]):
    community_id: CommunityID
    name: ListNameStr

    @property
    def list_id(self) -> ListID:
        return self.key[0]
