from domain import errors
from domain.entities.base import BaseEntity
from domain.types.id import ID
from domain.value_objects.community import CommunityLimits
from domain.value_objects.list import ListName
from domain.value_objects.string import StrStore


class ListEntity(BaseEntity):
    def __init__(self, id: ID, community_id: ID, name: ListName) -> None:
        super().__init__(id)

        self._community_id = community_id
        self.name = name

    @property
    def community_id(self) -> ID:
        return self._community_id

    @property
    def name(self) -> ListName:
        return self._name

    @name.setter
    def name(self, value: ListName) -> None:
        self._name = value
