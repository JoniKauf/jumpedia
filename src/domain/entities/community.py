from datetime import datetime

from domain.entities.base import BaseEntity
from domain.types.community import CommunityID
from domain.types.list import ListID
from domain.value_objects.community import CommunityLimits, CommunityNameStr
from domain.value_objects.datetime import DateTime


class CommunityEntity(BaseEntity[CommunityID]):
    def __init__(
        self,
        community_id: CommunityID,
        name: CommunityNameStr,
        default_selected_list_id: ListID | None,
        created_at: DateTime,
        limits: CommunityLimits,
    ) -> None:
        super().__init__(community_id)

        self.name = name
        self.default_selected_list_id = default_selected_list_id
        self._created_at = created_at
        self.limits = limits

    @property
    def community_id(self) -> CommunityID:
        return self._composite_key[0]

    @property
    def name(self) -> CommunityNameStr:
        return self._name

    @name.setter
    def name(self, value: CommunityNameStr) -> None:
        self._name = value

    @property
    def created(self) -> DateTime:
        return self._created_at

    @property
    def default_selected_list_id(self) -> ListID | None:
        return self._selected_list_id

    @default_selected_list_id.setter
    def default_selected_list_id(self, value: ListID | None) -> None:
        self._selected_list_id = value

    @property
    def limits(self) -> CommunityLimits:
        return self._limits

    @limits.setter
    def limits(self, value: CommunityLimits) -> None:
        self._limits = value
