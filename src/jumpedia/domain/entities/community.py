from jumpedia.domain.entities.base import BaseEntity
from jumpedia.domain.typing.community import CommunityID

lazy from jumpedia.domain.typing.list import ListID
lazy from jumpedia.domain.value_objects.community import (
    CommunityLimits,
    CommunityNameStr,
)
lazy from jumpedia.domain.value_objects.datetime import DateTimeWrapper
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CommunityEntity(BaseEntity[CommunityID]):
    name: CommunityNameStr
    default_selected_list_id: ListID | None
    created_at: DateTimeWrapper
    limits: CommunityLimits

    @property
    def community_id(self) -> CommunityID:
        return self.key[0]
