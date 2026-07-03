from sqlalchemy import select

from db.models import CommunityModel as CommunityModel
from db.models import ListModel
from db.models import ServerModel as ServerModel
from domain import errors
from domain.entities.community import CommunityEntity
from domain.entities.list import ListEntity
from domain.types.community import CommunityID
from domain.types.server import ServerID
from domain.value_objects.community import CommunityLimits, CommunityNameStr
from repositories.dtos.community import CommunityInsert
from repositories.list import list_model_to_entity

from .base import BaseRepository


def community_model_to_entity(model: CommunityModel) -> CommunityEntity:
    return CommunityEntity(
        community_id=model.community_id,
        name=CommunityNameStr(_real=model.real_name, _norm=model.norm_name),
        default_selected_list_id=model.default_selected_list_id,
        created=model.created,
        limits=CommunityLimits(
            community_list_count_max=model.community_list_count_max,
            list_attribute_count_max=model.list_attribute_count_max,
            list_task_count_max=model.list_task_count_max,
            attribute_alias_count_max=model.attribute_alias_count_max,
            field_slot_count_max=model.field_slot_count_max,
            collection_entry_count_max=model.collection_entry_count_max,
            collection_entry_alias_count_max=model.collection_entry_alias_count_max,
        ),
    )


class CommunityRepository(BaseRepository):
    # -------------------------
    # CREATE
    # -------------------------
    def create(self, community: CommunityInsert) -> CommunityEntity:
        obj = CommunityModel(
            norm_name=community.name.norm,
            real_name=community.name.real,
            default_selected_list_id=None,
            community_list_count_max=community.limits.community_list_count_max,
            list_attribute_count_max=community.limits.list_attribute_count_max,
            list_task_count_max=community.limits.list_task_count_max,
            attribute_alias_count_max=community.limits.attribute_alias_count_max,
            field_slot_count_max=community.limits.field_slot_count_max,
            collection_entry_count_max=community.limits.collection_entry_count_max,
            collection_entry_alias_count_max=community.limits.collection_entry_alias_count_max,
        )

        self._session.add(obj)
        self._session.flush()

        return community_model_to_entity(obj)

    # -------------------------
    # READ
    # -------------------------
    def get_by_id(self, community_id: CommunityID) -> CommunityEntity | None:
        obj = self._session.get(CommunityModel, community_id)
        return None if obj is None else community_model_to_entity(obj)

    def get_by_name(self, name: CommunityNameStr) -> CommunityEntity | None:
        stmt = select(CommunityModel).where(CommunityModel.norm_name == name.norm)
        obj = self._session.scalar(stmt)
        return None if obj is None else community_model_to_entity(obj)

    def get_all(self) -> tuple[CommunityEntity, ...]:
        stmt = select(CommunityModel)
        objs = self._session.scalars(stmt).all()
        return tuple(community_model_to_entity(o) for o in objs)

    # -------------------------
    # DELETE
    # -------------------------
    def delete(self, community_id: CommunityID) -> None:
        obj = self._session.get(CommunityModel, community_id)
        if obj is None:
            raise errors.NotFoundById(CommunityEntity)

        self._session.delete(obj)
        self._session.flush()

    def get_by_server_id(self, server_id: ServerID) -> CommunityEntity | None:
        stmt = (
            select(CommunityModel)
            .join(ServerModel, ServerModel.community_id == CommunityModel.community_id)
            .where(ServerModel.server_id == server_id)
        )
        obj = self._session.scalar(stmt)
        return None if obj is None else community_model_to_entity(obj)

    def get_default_selected_list(self, community_id: CommunityID) -> ListEntity | None:
        stmt = select(ListModel).where(
            ListModel.list_id
            == (
                select(CommunityModel.default_selected_list_id)
                .where(CommunityModel.community_id == community_id)
                .scalar_subquery()
            )
        )
        obj = self._session.execute(stmt).scalar_one_or_none()

        return None if obj is None else list_model_to_entity(obj)

    def update(self, community: CommunityEntity) -> None:
        obj = self._session.get(CommunityModel, community.community_id)

        if obj is None:
            raise errors.NotFoundById(CommunityEntity)

        obj.norm_name = community.name.norm
        obj.real_name = community.name.real

        obj.default_selected_list_id = community.default_selected_list_id

        obj.community_list_count_max = community.limits.community_list_count_max
        obj.list_attribute_count_max = community.limits.list_attribute_count_max
        obj.list_task_count_max = community.limits.list_task_count_max
        obj.attribute_alias_count_max = community.limits.attribute_alias_count_max
        obj.field_slot_count_max = (
            community.limits.field_slot_count_max
        )
        obj.collection_entry_count_max = (
            community.limits.collection_entry_count_max
        )
        obj.collection_entry_alias_count_max = (
            community.limits.collection_entry_alias_count_max
        )

        self._session.flush()
