from sqlalchemy import func, or_, select

from db.models import ListModel, TaskModel, TaskAliasModel
from domain.entities.task import TaskEntity
from domain.types.community import CommunityID
from domain.types.list import ListID
from domain.types.task import TaskID
from domain.value_objects.task_attribute_slot import TaskAttributeSlot
from repositories.dtos.task import TaskAliasInsert, TaskInsert
import typing as t

from .base import BaseRepository


def task_model_to_entity(model: TaskModel) -> TaskEntity:
    return TaskEntity(
        model.task_id,
        model.list_id,
        TaskAttributeSlot(_real=model.real_name, _norm=model.norm_name)
    )

class TaskRepository(BaseRepository):
    def create(self, task: TaskInsert) -> TaskEntity:
        obj = TaskModel(
            list_id=task.list_id,
            norm_name=task.name.norm,
            slot_name=task.name.real,
        )

        self.session.add(obj)
        self.session.flush()
        
        return task_model_to_entity(obj)

    def get_by_id(self, task_id: int) -> TaskModel | None:
        return self.session.get(TaskModel, task_id)

    def count_by_list(self, list_id: ListID) -> int:
        stmt = select(func.count()).select_from(TaskModel).where(TaskModel.list_id == list_id)
        return self.session.scalar(stmt) or 0

    def count_by_community(self, community_id: CommunityID) -> int:
        stmt = (
            select(func.count())
            .select_from(TaskModel)
            .join(ListModel, ListModel.list_id == TaskModel.list_id)
            .where(ListModel.community_id == community_id)
        )

        return self.session.scalar(stmt) or 0

    def count_grouped_by_community_id(self) -> dict[CommunityID, int]:
        stmt = (
            select(
                ListModel.community_id,
                func.count(),
            )
            .join(TaskModel, TaskModel.list_id == ListModel.list_id)
            .group_by(ListModel.community_id)
        )

        return {
            CommunityID(community_id): count
            for community_id, count in self.session.execute(stmt)
        }

    def count_grouped_by_list_id(
        self,
        community_id: CommunityID,
    ) -> dict[ListID, int]:
        stmt = (
            select(
                TaskModel.list_id,
                func.count(),
            )
            .join(ListModel, ListModel.list_id == TaskModel.list_id)
            .where(ListModel.community_id == community_id)
            .group_by(TaskModel.list_id)
        )

        return {ListID(list_id): count for list_id, count in self.session.execute(stmt)}

    def get_syn_to_task_by_list_id(
        self,
        list_id: ListID,
    ) -> dict[TaskAttributeSlot, TaskEntity]:
        stmt = (
            select(TaskModel, TaskAliasModel)
            .outerjoin(
                TaskAliasModel,
                TaskAliasModel.task_id == TaskModel.task_id,
            )
            .where(TaskModel.list_id == list_id)
        )

        res: dict[TaskAttributeSlot, TaskEntity] = {}
        id_to_entity: dict[TaskID, TaskEntity] = {}

        for task_obj, alias_obj in self.session.execute(stmt):
            task_obj: TaskModel
            alias_obj: TaskAliasModel | None

            entity = id_to_entity.get(task_obj.task_id)

            if entity is None:
                entity = task_model_to_entity(task_obj)
                id_to_entity[task_obj.task_id] = entity
                res[entity.name] = entity

            if alias_obj is not None:
                res[
                    TaskAttributeSlot(
                        _real=alias_obj.real_alias,
                        _norm=alias_obj.norm_alias,
                    )
                ] = entity

        return res
    

    def get_by_list_id_and_any_syn(
        self,
        list_id: ListID,
        syns: t.Iterable[TaskAttributeSlot],
    ) -> tuple[TaskEntity, TaskAttributeSlot] | None:
        syns = tuple(syns)
        norms = {syn.norm for syn in syns}

        if not norms:
            return None

        stmt = (
            select(TaskModel, TaskAliasModel)
            .outerjoin(
                TaskAliasModel,
                TaskAliasModel.task_id == TaskModel.task_id,
            )
            .where(
                TaskModel.list_id == list_id,
                or_(
                    TaskModel.norm_name.in_(norms),
                    TaskAliasModel.norm_alias.in_(norms),
                ),
            )
            .limit(1)
        )

        row = self.session.execute(stmt).first()

        if row is None:
            return None

        task_obj, alias_obj = row
        task_obj: TaskModel
        alias_obj: TaskAliasModel | None

        entity = task_model_to_entity(task_obj)

        if task_obj.norm_name in norms:
            syn = TaskAttributeSlot(
                _real=task_obj.real_name,
                _norm=task_obj.norm_name,
            )
        else:
            assert alias_obj is not None
            syn = TaskAttributeSlot(
                _real=alias_obj.real_alias,
                _norm=alias_obj.norm_alias,
            )

        return entity, syn
    
    def create_many_aliases(
        self, task_aliases: t.Iterable[TaskAliasInsert]
    ) -> None:
        objs = tuple(
            TaskAliasModel(
                task_id=task_alias.task_id,
                list_id=task_alias.list_id,
                norm_alias=task_alias.alias.norm,
                real_alias=task_alias.alias.real,
            )
            for task_alias in task_aliases
        )

        self.session.add_all(objs)
        self.session.flush()