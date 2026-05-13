from discord import Interaction

from db.models import List
from domain.value_objects.strings import StrStore
from repositories.attribute import AttributeRepository
from repositories.list import ListRepository
from repositories.community import CommunityRepository
from sqlalchemy.orm import Session
from domain import errors
from services.dto.list import ListInfo

from .base import BaseService

class ListService(BaseService):
    def __init__(self, session: Session) -> None:
        super().__init__(session)

        self.list_repo = ListRepository(session)
        self.attribute_repo = AttributeRepository(session)


    def info(self, server_id: int, name: StrStore) -> ListInfo:
        community = self._get_community_by_server_id_or_throw(server_id)

        lst = self.list_repo.get_by_name(community.community_id, name)

        if lst is None:
            raise errors.NotFound(List)

        attributes = self.attribute_repo.get_by_list_id(lst.list_id)

        static_attrs = tuple(
            attr.real_name for attr in attributes if attr.type_id == 1
        )

        task_attrs = tuple(
            attr.real_name for attr in attributes if attr.type_id == 2
        )

        user_attrs = tuple(
            attr.real_name for attr in attributes if attr.type_id == 3
        )

        task_count = self.list_repo.count_tasks(lst.list_id)

        is_default = self.community_repo.get_default_list_id(lst.community_id) == lst.list_id

        return ListInfo(
            name=lst.real_name,
            static_attribute=static_attrs,
            task_attribute=task_attrs,
            user_attribute=user_attrs,
            task_count=task_count,
            is_default_selected_list=is_default,
        )

    # -------------------------
    # CREATE LIST
    # -------------------------
    def create_list(self, community_id: int, name: str):
        canon_name = strings.StrStore(name)

        del name

        community = self.community_repo.get_by_id(community_id)

        if community is None:
            raise ValueError("community not found")

        existing_lists = self.list_repo.get_by_community(community_id)

        if len(existing_lists) >= community.community_list_count_max:
            raise ValueError("list limit reached")

        if self.list_repo.get_by_name(community_id, canon_name):
            raise ValueError("list already exists")

        return self.list_repo.create(
            community_id=community_id,
            name=canon_name
        )

    # -------------------------
    # DELETE LIST
    # -------------------------
    def delete_list(self, community_id: int, list_id: int):
        lst = self.list_repo.get_by_id(list_id)
        if not lst or lst.community_id != community_id:
            raise ValueError("list not found")

        self.list_repo.delete(list_id)

    # -------------------------
    # RENAME LIST
    # -------------------------
    def rename_list(self, community_id: int, list_id: int, new_name: str):
        lst = self.list_repo.get_by_id(list_id)

        if not lst or lst.community_id != community_id:
            raise ValueError("list not found")
        
        canon_name = strings.StrStore(new_name)

        if self.list_repo.get_by_name(community_id, canon_name):
            raise ValueError("name already taken")

        lst.norm_name = canon_name.norm
        lst.real_name = canon_name.real