from domain.value_objects import s
from repository.list import ListRepository
from repository.community import CommunityRepository
from sqlalchemy.orm import Session

from .base import BaseService

class ListService(BaseService):
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repo = ListRepository(session)
        self.community_repo = CommunityRepository(session)

    # -------------------------
    # CREATE LIST
    # -------------------------
    def create_list(self, community_id: int, name: str):
        canon_name = s.StrStore(name)

        del name

        community = self.community_repo.get_by_id(community_id)

        if community is None:
            raise ValueError("community not found")

        existing_lists = self.repo.get_by_community(community_id)

        if len(existing_lists) >= community.community_list_count_max:
            raise ValueError("list limit reached")

        if self.repo.get_by_name(community_id, canon_name):
            raise ValueError("list already exists")

        return self.repo.create(
            community_id=community_id,
            name=canon_name
        )

    # -------------------------
    # DELETE LIST
    # -------------------------
    def delete_list(self, community_id: int, list_id: int):
        lst = self.repo.get_by_id(list_id)
        if not lst or lst.community_id != community_id:
            raise ValueError("list not found")

        self.repo.delete(list_id)

    # -------------------------
    # RENAME LIST
    # -------------------------
    def rename_list(self, community_id: int, list_id: int, new_name: str):
        lst = self.repo.get_by_id(list_id)

        if not lst or lst.community_id != community_id:
            raise ValueError("list not found")
        
        canon_name = s.StrStore(new_name)

        if self.repo.get_by_name(community_id, canon_name):
            raise ValueError("name already taken")

        lst.norm_name = canon_name.norm
        lst.real_name = canon_name.real