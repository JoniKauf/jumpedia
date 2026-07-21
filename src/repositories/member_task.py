from sqlalchemy import select

from db.models import MemberModel, MemberTaskModel, TaskModel, UserModel
from domain.entities.member import MemberEntity
from domain.entities.member_task import MemberTaskEntity
from domain.entities.task import TaskEntity
from domain.errors.internal import NotFoundById
from domain.typing.list import ListID
from domain.typing.member import MemberID
from domain.typing.member_task import MemberTaskID
from domain.typing.task import TaskID
from domain.value_objects.datetime import DateTimeWrapper
from repositories.base import BaseRepository
from repositories.dtos.member_task import MemberTaskInsert
from repositories.member import member_model_to_entity
from repositories.task import task_model_to_entity
from repositories.user import user_model_to_entity


def member_task_model_to_entity(model: MemberTaskModel) -> MemberTaskEntity:
    return MemberTaskEntity(
        member_task_id=model.member_task_id,
        member_id=model.member_id,
        task_id=model.task_id,
        given_at=DateTimeWrapper(model.given_at),
        given_by=model.given_by,
    )


class MemberTaskRepository(BaseRepository):
    def create(self, member_task: MemberTaskInsert) -> MemberTaskEntity:
        obj = MemberTaskModel(
            member_id=member_task.member_id,
            task_id=member_task.task_id,
            given_by=member_task.given_by,
        )

        self._session.add(obj)
        self._session.flush()

        return member_task_model_to_entity(obj)

    def get_by_member_id_and_task_id(
        self, member_id: MemberID, task_id: TaskID
    ) -> MemberTaskEntity | None:
        stmt = select(MemberTaskModel).where(
            MemberTaskModel.member_id == member_id, MemberTaskModel.task_id == task_id
        )

        obj = self._session.scalar(stmt)

        return None if obj is None else member_task_model_to_entity(obj)

    def get_by_id(self, member_task_id: int) -> MemberTaskModel | None:
        return self._session.get(MemberTaskModel, member_task_id)

    def delete(self, member_task_id: MemberTaskID) -> None:
        obj = self._session.get(MemberTaskModel, member_task_id)

        if obj is None:
            raise NotFoundById(MemberTaskEntity)

        self._session.delete(obj)
        self._session.flush()

    def get_member_tasks_and_tasks_by_list_id_and_member_id(
        self,
        list_id: ListID,
        member_id: MemberID,
    ) -> frozendict[MemberTaskEntity, TaskEntity]:
        stmt = (
            select(MemberTaskModel, TaskModel)
            .join(TaskModel, MemberTaskModel.task_id == TaskModel.task_id)
            .where(
                MemberTaskModel.member_id == member_id,
                TaskModel.list_id == list_id,
            )
        )

        return frozendict(
            (member_task_model_to_entity(member_task), task_model_to_entity(task))
            for member_task, task in self._session.execute(stmt).tuples()
        )

    def get_given_by_member_by_list_id_and_member_id(
        self,
        list_id: ListID,
        member_id: MemberID,
    ) -> frozendict[MemberTaskID, MemberEntity]:
        stmt = (
            select(MemberTaskModel, MemberModel, UserModel)
            .join(TaskModel, MemberTaskModel.task_id == TaskModel.task_id)
            .join(MemberModel, MemberTaskModel.given_by == MemberModel.member_id)
            .join(UserModel, MemberModel.user_id == UserModel.user_id)
            .where(
                MemberTaskModel.member_id == member_id,
                TaskModel.list_id == list_id,
            )
        )

        return frozendict(
            (
                member_task.member_task_id,
                member_model_to_entity(member, user_model_to_entity(user)),
            )
            for member_task, member, user in self._session.execute(stmt).tuples()
        )
