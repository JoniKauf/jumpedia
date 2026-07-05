import types as ts
import typing as t

from sqlalchemy import delete, func, or_, select

from db.models import ListModel, TaskAliasModel, TaskModel
from domain import errors
from domain.entities.task import TaskEntity
from domain.types.community import CommunityID
from domain.types.list import ListID
from domain.types.task import TaskID
from domain.value_objects.field_slot import FieldSlotStr
from domain.value_objects.index import Index
from repositories.dtos.task import TaskAliasInsert, TaskInsert

from .base import BaseRepository


def task_model_to_entity(model: TaskModel) -> TaskEntity:
    return TaskEntity(
        task_id=model.task_id,
        list_id=model.list_id,
        name=FieldSlotStr(_real=model.real_name, _norm=model.norm_name),
    )


class TaskRepository(BaseRepository):
    def create(self, task: TaskInsert) -> TaskEntity:
        obj = TaskModel(
            list_id=task.list_id,
            norm_name=task.name.norm,
            slot_name=task.name.real,
        )

        self._session.add(obj)
        self._session.flush()

        return task_model_to_entity(obj)

    def get_by_id(self, task_id: int) -> TaskModel | None:
        return self._session.get(TaskModel, task_id)

    def get_all_by_list_id(self, list_id: ListID) -> tuple[TaskEntity, ...]:
        stmt = select(TaskModel).where(TaskModel.list_id == list_id)
        objs = self._session.scalars(stmt).all()
        return tuple(task_model_to_entity(o) for o in objs)

    def count_by_list(self, list_id: ListID) -> int:
        stmt = (
            select(func.count())
            .select_from(TaskModel)
            .where(TaskModel.list_id == list_id)
        )
        return self._session.scalar(stmt) or 0

    def count_by_community(self, community_id: CommunityID) -> int:
        stmt = (
            select(func.count())
            .select_from(TaskModel)
            .join(ListModel, ListModel.list_id == TaskModel.list_id)
            .where(ListModel.community_id == community_id)
        )

        return self._session.scalar(stmt) or 0

    def count_grouped_by_community_id(self) -> ts.MappingProxyType[CommunityID, int]:
        stmt = (
            select(
                ListModel.community_id,
                func.count(),
            )
            .join(TaskModel, TaskModel.list_id == ListModel.list_id)
            .group_by(ListModel.community_id)
        )

        return ts.MappingProxyType(
            {
                CommunityID(community_id): count
                for community_id, count in self._session.execute(stmt)
            }
        )

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

        return {
            ListID(list_id): count for list_id, count in self._session.execute(stmt)
        }

    def get_syn_to_task_by_list_id(
        self,
        list_id: ListID,
    ) -> dict[FieldSlotStr, TaskEntity]:
        stmt = (
            select(TaskModel, TaskAliasModel)
            .outerjoin(
                TaskAliasModel,
                TaskAliasModel.task_id == TaskModel.task_id,
            )
            .where(TaskModel.list_id == list_id)
        )

        res: dict[FieldSlotStr, TaskEntity] = {}
        id_to_entity: dict[TaskID, TaskEntity] = {}

        for task_obj, alias_obj in self._session.execute(stmt):
            task_obj: TaskModel
            alias_obj: TaskAliasModel | None

            entity = id_to_entity.get(task_obj.task_id)

            if entity is None:
                entity = task_model_to_entity(task_obj)
                id_to_entity[task_obj.task_id] = entity
                res[entity.name] = entity

            if alias_obj is not None:
                res[
                    FieldSlotStr(
                        _real=alias_obj.real_alias,
                        _norm=alias_obj.norm_alias,
                    )
                ] = entity

        return res

    def get_first_by_list_id_and_any_syn(
        self,
        list_id: ListID,
        syns: t.Iterable[FieldSlotStr],
        exclude: TaskID | None
    ) -> tuple[TaskEntity, FieldSlotStr] | None:
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

        if exclude is not None:
            stmt = stmt.where(TaskModel.task_id != exclude)

        row = self._session.execute(stmt).first()

        if row is None:
            return None

        task_obj, alias_obj = row
        task_obj: TaskModel
        alias_obj: TaskAliasModel | None

        entity = task_model_to_entity(task_obj)

        if task_obj.norm_name in norms:
            syn = FieldSlotStr(
                _real=task_obj.real_name,
                _norm=task_obj.norm_name,
            )
        else:
            assert alias_obj is not None
            syn = FieldSlotStr(
                _real=alias_obj.real_alias,
                _norm=alias_obj.norm_alias,
            )

        return entity, syn

    def create_many_aliases(self, task_aliases: t.Iterable[TaskAliasInsert]) -> None:
        objs = tuple(
            TaskAliasModel(
                task_id=task_alias.task_id,
                index=task_alias.index.value,
                list_id=task_alias.list_id,
                norm_alias=task_alias.alias.norm,
                real_alias=task_alias.alias.real,
            )
            for task_alias in task_aliases
        )

        self._session.add_all(objs)
        self._session.flush()

    def delete(self, task_id: TaskID) -> None:
        obj = self._session.get(TaskModel, task_id)

        if obj is None:
            raise errors.NotFoundById(TaskEntity)

        self._session.delete(obj)
        self._session.flush()

    def get_by_list_id_and_name(
        self,
        list_id: ListID,
        name: FieldSlotStr,
    ) -> TaskEntity | None:
        stmt = select(TaskModel).where(
            TaskModel.list_id == list_id,
            TaskModel.norm_name == name.norm,
        )

        obj = self._session.scalar(stmt)

        return None if obj is None else task_model_to_entity(obj)

    def get_by_list_id_and_syn(
        self,
        list_id: ListID,
        syn: FieldSlotStr,
    ) -> tuple[TaskEntity, FieldSlotStr] | None:
        stmt = (
            select(TaskModel, TaskAliasModel)
            .outerjoin(
                TaskAliasModel,
                TaskAliasModel.task_id == TaskModel.task_id,
            )
            .where(
                TaskModel.list_id == list_id,
                or_(
                    TaskModel.norm_name == syn.norm,
                    TaskAliasModel.norm_alias == syn.norm,
                ),
            )
            .limit(1)
        )

        row = self._session.execute(stmt).first()

        if row is None:
            return None

        task_obj, alias_obj = row
        task_obj: TaskModel
        alias_obj: TaskAliasModel | None

        entity = task_model_to_entity(task_obj)

        if task_obj.norm_name == syn.norm:
            colliding_syn = FieldSlotStr(
                _real=task_obj.real_name,
                _norm=task_obj.norm_name,
            )
        else:
            assert alias_obj is not None
            colliding_syn = FieldSlotStr(
                _real=alias_obj.real_alias,
                _norm=alias_obj.norm_alias,
            )

        return entity, colliding_syn

    def get_aliases_by_task_id(
        self,
        task_id: TaskID,
    ) -> tuple[FieldSlotStr, ...]:
        stmt = (
            select(TaskAliasModel)
            .where(TaskAliasModel.task_id == task_id)
            .order_by(TaskAliasModel.index.asc())
        )

        return tuple(
            FieldSlotStr(
                _real=obj.real_alias,
                _norm=obj.norm_alias,
            )
            for obj in self._session.scalars(stmt)
        )

    def get_grouped_aliases_by_list_id(
        self,
        list_id: ListID,
    ) -> ts.MappingProxyType[TaskID, tuple[FieldSlotStr, ...]]:
        stmt = (
            select(TaskAliasModel)
            .join(
                TaskModel,
                TaskModel.task_id == TaskAliasModel.task_id,
            )
            .where(
                TaskModel.list_id == list_id,
            )
            .order_by(
                TaskAliasModel.task_id.asc(),
                TaskAliasModel.index.asc(),
            )
        )

        res: dict[TaskID, list[FieldSlotStr]] = {}

        for obj in self._session.scalars(stmt):
            res.setdefault(obj.task_id, []).append(
                FieldSlotStr(
                    _real=obj.real_alias,
                    _norm=obj.norm_alias,
                )
            )

        return ts.MappingProxyType(
            {task_id: tuple(aliases) for task_id, aliases in res.items()}
        )

    def update_name(
        self,
        task_id: TaskID,
        name: FieldSlotStr,
    ) -> None:
        obj = self._session.get(TaskModel, task_id)

        if obj is None:
            raise errors.NotFoundById(TaskEntity)

        obj.real_name = name.real
        obj.norm_name = name.norm

        self._session.flush()

    def update_aliases(
        self,
        task_id: TaskID,
        aliases: t.Iterable[TaskAliasInsert],
    ) -> None:
        self._session.execute(
            delete(TaskAliasModel).where(
                TaskAliasModel.task_id == task_id,
            )
        )

        objs = tuple(
            TaskAliasModel(
                task_id=task_id,
                index=alias.index.value,
                list_id=alias.list_id,
                real_alias=alias.alias.real,
                norm_alias=alias.alias.norm,
            )
            for alias in aliases
        )

        if objs:
            self._session.add_all(objs)

        self._session.flush()