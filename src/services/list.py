from discord import Interaction

from db.models import List
from domain.entities.list import ListEntity
from domain.value_objects.string import StrStore
from repositories.attribute import AttributeRepository
from repositories.list import ListRepository
from sqlalchemy.orm import Session
from domain import errors
from services.dtos.list import ListInfoDTO

from .base import BaseService


class ListService(BaseService):
    def __init__(self, session: Session) -> None:
        super().__init__(session)

        self.list_repo = ListRepository(session)
        self.attribute_repo = AttributeRepository(session)

    def info(self, server_id: int, name: StrStore) -> ListInfoDTO:
        community = self._get_community_by_server_id_or_throw(server_id)

        lst = self.list_repo.get_by_name(community.id, name)

        if lst is None:
            raise errors.NotFound(List)

        attributes = self.attribute_repo.get_by_list_id(lst.id)
        task_count = self.list_repo.count_tasks(lst.id)
        is_default = (
            self.community_repo.get_default_selected_list(lst.community_id) == lst.id
        )

        return ListInfoDTO(
            name=lst.name,
            attributes=tuple(attributes),
            task_count=task_count,
            is_default_selected_list=is_default,
        )

    # -------------------------
    # CREATE LIST
    # -------------------------
    def create(self, community_id: int, name: StrStore) -> ListEntity:
        community = self.community_repo.get_by_id(community_id)

        if community is None:
            raise ValueError("community not found")

        list_count = self.list_repo.count(community_id)

        if list_count >= community.limits.community_list_count_max:
            raise ValueError("list limit reached")

        if self.list_repo.get_by_name(community_id, name):
            raise ValueError("list already exists")

        return self.list_repo.create(community_id=community_id, name=name)

    # -------------------------
    # DELETE LIST
    # -------------------------
    def delete(self, community_id: int, list_id: int):
        lst = self.list_repo.get_by_id(list_id)

        if not lst or lst.community_id != community_id:
            raise ValueError("list not found")

        self.list_repo.delete(list_id)

    # -------------------------
    # RENAME LIST
    # -------------------------
    def rename(self, list_id: int, new_name: StrStore):
        lst = self.list_repo.get_by_id(list_id)

        if lst is None:
            raise ValueError("list not found")

        if self.list_repo.get_by_name(lst.community_id, lst.name):
            raise ValueError("name already taken")

        lst.name = name
