from dataclasses import asdict

from sqlalchemy import func, select, delete

from db.models import Community as Community, CommunityUser, List, Server as Server
from domain import errors
from domain.entities.community import CommunityEntity
from domain.entities.list import ListEntity
from domain.entities.user import CommunityUserEntity
from domain.types.id import ID
from domain.value_objects.community import CommunityName
from domain.value_objects.limits import Limits
from domain.value_objects.string import StrStore
from repositories.dtos.community import CreateCommunityDTO
from repositories.list import _list_model_to_entity
from .base import BaseRepository
import typing as t


def _community_model_to_entity(model: Community) -> CommunityEntity:
    return CommunityEntity(
        id=model.community_id,
        name=CommunityName(_real=model.real_name, _norm=model.norm_name),
        default_selected_list_id=model.default_selected_list_id,
        limits=Limits(
            community_list_count_max=model.community_list_count_max,
            list_attribute_count_max=model.list_attribute_count_max,
            list_task_count_max=model.list_task_count_max,
            attribute_alias_count_max=model.attribute_alias_count_max,
            attribute_task_value_slot_count_max=model.attribute_task_value_slot_count_max,
            attribute_collection_entry_count_max=model.attribute_collection_entry_count_max,
            attribute_collection_entry_alias_count_max=model.attribute_collection_entry_alias_count_max,
        ),
    )


class CommunityRepository(BaseRepository):
    # -------------------------
    # CREATE
    # -------------------------
    def create(self, community: CreateCommunityDTO) -> CommunityEntity:
        obj = Community(
            norm_name=community.name.norm,
            real_name=community.name.real,
            default_selected_list_id=None,
            community_list_count_max=community.limits.community_list_count_max,
            list_attribute_count_max=community.limits.list_attribute_count_max,
            list_task_count_max=community.limits.list_task_count_max,
            attribute_alias_count_max=community.limits.attribute_alias_count_max,
            attribute_task_value_slot_count_max=community.limits.attribute_task_value_slot_count_max,
            attribute_collection_entry_count_max=community.limits.attribute_collection_entry_count_max,
            attribute_collection_entry_alias_count_max=community.limits.attribute_collection_entry_alias_count_max,
        )

        self.session.add(obj)
        self.session.flush()

        return _community_model_to_entity(obj)

    # -------------------------
    # READ
    # -------------------------
    def get_by_id(self, community_id: ID) -> CommunityEntity | None:
        obj = self.session.get(Community, community_id)
        return None if obj is None else _community_model_to_entity(obj)

    def get_by_name(self, name: CommunityName) -> CommunityEntity | None:
        stmt = select(Community).where(Community.norm_name == name.norm)
        obj = self.session.scalar(stmt)
        return None if obj is None else _community_model_to_entity(obj)

    def get_all(self) -> list[CommunityEntity]:
        stmt = select(Community)
        objs = self.session.scalars(stmt).all()
        return [_community_model_to_entity(o) for o in objs]

    # -------------------------
    # DELETE
    # -------------------------
    def delete(self, community_id: ID) -> None:
        obj = self.session.get(Community, community_id)
        if obj is not None:
            self.session.delete(obj)
            self.session.flush()

    def get_by_server_id(self, server_id: ID) -> CommunityEntity | None:
        stmt = (
            select(Community)
            .join(Server, Server.community_id == Community.community_id)
            .where(Server.server_id == server_id)
        )
        obj = self.session.scalar(stmt)
        return None if obj is None else _community_model_to_entity(obj)

    def get_default_selected_list(self, community_id: ID) -> ListEntity | None:
        stmt = select(List).where(
            List.list_id
            == (
                select(Community.default_selected_list_id)
                .where(Community.community_id == community_id)
                .scalar_subquery()
            )
        )
        obj = self.session.execute(stmt).scalar_one_or_none()

        return None if obj is None else _list_model_to_entity(obj)
