from domain import errors
from domain.entities.base import BaseEntity
from domain.types.id import ID
from domain.value_objects.community import CommunityName
from domain.value_objects.community import CommunityLimits
from domain.value_objects.string import StrStore


class CommunityEntity(BaseEntity):
    def __init__(
        self,
        id: ID,
        name: CommunityName,
        default_selected_list_id: ID | None,
        limits: CommunityLimits,
    ) -> None:
        super().__init__(id)

        self.name = name
        self.default_selected_list_id = default_selected_list_id
        self.limits = limits

    @property
    def name(self) -> CommunityName:
        return self._name

    @name.setter
    def name(self, value: CommunityName) -> None:
        self._name = value

    @property
    def limits(self) -> CommunityLimits:
        return self._limits

    @limits.setter
    def limits(self, value: CommunityLimits) -> None:
        self._limits = value

    @property
    def default_selected_list_id(self) -> ID | None:
        return self._selected_list_id

    @default_selected_list_id.setter
    def default_selected_list_id(self, value: ID | None) -> None:
        self._selected_list_id = value
