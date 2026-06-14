from datetime import datetime

from domain.entities.base import BaseEntity
from domain.types.community import CommunityID
from domain.types.list import ListID
from domain.value_objects.community import CommunityName
from domain.value_objects.community import CommunityLimits


class CommunityEntity(BaseEntity[CommunityID]):
    def __init__(
        self,
        id: CommunityID,
        name: CommunityName,
        default_selected_list_id: ListID | None,
        created: datetime,
        limits: CommunityLimits,
    ) -> None:
        super().__init__(id)

        self.name = name
        self.default_selected_list_id = default_selected_list_id
        self._created = created
        self.limits = limits

    @property
    def name(self) -> CommunityName:
        return self._name

    @name.setter
    def name(self, value: CommunityName) -> None:
        self._name = value

    @property
    def created(self) -> datetime:
        return self._created

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
