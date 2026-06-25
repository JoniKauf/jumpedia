from sqlalchemy import func, or_, select

from db.models import List, Task, TaskAlias
from domain.entities.task import TaskEntity
from domain.types.community import CommunityID
from domain.types.list import ListID
from domain.types.task import TaskID
from domain.value_objects.task_value_slot import TaskValueSlot
from repositories.dtos.task import TaskInsert
import typing as t

from .base import BaseRepository


def task_model_to_entity(model: Task) -> TaskEntity:
    return TaskEntity(
        model.task_id,
        model.list_id,
        TaskValueSlot(_real=model.real_name, _norm=model.norm_name)
    )

class TaskRepository(BaseRepository):
    def create(self, task: TaskInsert) -> TaskEntity:
        obj = Task(
            list_id=task.list_id,
            norm_name=task.name.norm,
            slot_name=task.name.real,
        )

        self.session.add(obj)
        self.session.flush()

        return task_model_to_entity(obj)

    def get_by_id(self, task_id: int) -> Task | None:
        return self.session.get(Task, task_id)

    def count_by_list(self, list_id: ListID) -> int:
        stmt = select(func.count()).select_from(Task).where(Task.list_id == list_id)
        return self.session.scalar(stmt) or 0

    def count_by_community(self, community_id: CommunityID) -> int:
        stmt = (
            select(func.count())
            .select_from(Task)
            .join(List, List.list_id == Task.list_id)
            .where(List.community_id == community_id)
        )

        return self.session.scalar(stmt) or 0

    def count_grouped_by_community_id(self) -> dict[CommunityID, int]:
        stmt = (
            select(
                List.community_id,
                func.count(),
            )
            .join(Task, Task.list_id == List.list_id)
            .group_by(List.community_id)
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
                Task.list_id,
                func.count(),
            )
            .join(List, List.list_id == Task.list_id)
            .where(List.community_id == community_id)
            .group_by(Task.list_id)
        )

        return {ListID(list_id): count for list_id, count in self.session.execute(stmt)}

    def get_syn_to_task_by_list_id(
        self,
        list_id: ListID,
    ) -> dict[TaskValueSlot, TaskEntity]:
        stmt = (
            select(Task, TaskAlias)
            .outerjoin(
                TaskAlias,
                TaskAlias.task_id == Task.task_id,
            )
            .where(Task.list_id == list_id)
        )

        res: dict[TaskValueSlot, TaskEntity] = {}
        id_to_entity: dict[TaskID, TaskEntity] = {}

        for task_obj, alias_obj in self.session.execute(stmt):
            task_obj: Task
            alias_obj: TaskAlias | None

            entity = id_to_entity.get(task_obj.task_id)

            if entity is None:
                entity = task_model_to_entity(task_obj)
                id_to_entity[task_obj.task_id] = entity
                res[entity.name] = entity

            if alias_obj is not None:
                res[
                    TaskValueSlot(
                        _real=alias_obj.real_alias,
                        _norm=alias_obj.norm_alias,
                    )
                ] = entity

        return res
    

    def get_by_list_id_and_any_syn(
        self,
        list_id: ListID,
        syns: t.Iterable[TaskValueSlot],
    ) -> tuple[TaskEntity, TaskValueSlot] | None:
        syns = tuple(syns)
        norms = {syn.norm for syn in syns}

        if not norms:
            return None

        stmt = (
            select(Task, TaskAlias)
            .outerjoin(
                TaskAlias,
                TaskAlias.task_id == Task.task_id,
            )
            .where(
                Task.list_id == list_id,
                or_(
                    Task.norm_name.in_(norms),
                    TaskAlias.norm_alias.in_(norms),
                ),
            )
            .limit(1)
        )

        row = self.session.execute(stmt).first()

        if row is None:
            return None

        task_obj, alias_obj = row
        task_obj: Task
        alias_obj: TaskAlias | None

        entity = task_model_to_entity(task_obj)

        if task_obj.norm_name in norms:
            syn = TaskValueSlot(
                _real=task_obj.real_name,
                _norm=task_obj.norm_name,
            )
        else:
            assert alias_obj is not None
            syn = TaskValueSlot(
                _real=alias_obj.real_alias,
                _norm=alias_obj.norm_alias,
            )

        return entity, syn