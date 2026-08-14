from jumpedia.domain.entities.base import BaseEntity

lazy from jumpedia.domain.typing.community import CommunityID
from jumpedia.domain.typing.list import ListID

lazy from jumpedia.domain.value_objects.list import ListNameStr
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ListEntity(BaseEntity[ListID]):
    community_id: CommunityID
    name: ListNameStr

    @property
    def list_id(self) -> ListID:
        return self.key[0]
