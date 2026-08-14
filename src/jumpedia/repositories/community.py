from sqlalchemy import select

from jumpedia.db.models import CommunityModel as CommunityModel
from jumpedia.db.models import ListModel
from jumpedia.db.models import ServerModel as ServerModel
from jumpedia.domain.entities.community import CommunityEntity
from jumpedia.domain.entities.list import ListEntity
from jumpedia.domain.errors.internal import NotFoundById
from jumpedia.domain.typing.community import CommunityID
from jumpedia.domain.typing.list import ListID
from jumpedia.domain.typing.server import ServerID
from jumpedia.domain.value_objects.community import CommunityLimits, CommunityNameStr
from jumpedia.domain.value_objects.datetime import DateTimeWrapper
from jumpedia.repositories.dtos.community import CommunityInsert
from jumpedia.repositories.list import list_model_to_entity

from .base import BaseRepository


def community_model_to_entity(model: CommunityModel) -> CommunityEntity:
    return CommunityEntity(
        key=(model.community_id,),
        name=CommunityNameStr._create_from_real_and_hash(model.name, model.name_hash),
        default_selected_list_id=model.default_selected_list_id,
        created_at=DateTimeWrapper(model.created_at),
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
    def create(self, community: CommunityInsert) -> CommunityEntity:
        obj = CommunityModel(
            name_hash=community.name.hash,
            name=community.name.real,
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

    def get_by_name(self, name: CommunityNameStr) -> CommunityEntity | None:
        stmt = select(CommunityModel).where(CommunityModel.name_hash == name.hash)
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
            raise NotFoundById(CommunityEntity, community_id)

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

    def update_default_selected_list_id(
        self, community_id: CommunityID, default_selected_list_id: ListID | None
    ) -> None:
        obj = self._session.get(CommunityModel, community_id)

        if obj is None:
            raise NotFoundById(CommunityEntity, community_id)

        obj.default_selected_list_id = default_selected_list_id

        self._session.flush()

    def lock(self, community_id: int) -> None:
        self._session.execute(
            select(CommunityModel)
            .where(CommunityModel.community_id == community_id)
            .with_for_update()
        )
