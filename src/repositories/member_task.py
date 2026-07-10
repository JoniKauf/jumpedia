from sqlalchemy import select

from db.models import MemberTaskModel
from domain.entities.member_task import MemberTaskEntity
from domain.errors import business
from domain.types.member import MemberID
from domain.types.member_task import MemberTaskID
from domain.types.task import TaskID
from repositories.base import BaseRepository
from repositories.dtos.member_task import MemberTaskInsert


def member_task_model_to_entity(model: MemberTaskModel) -> MemberTaskEntity:
    return MemberTaskEntity(
        member_task_id=model.member_task_id,
        member_id=model.member_id,
        task_id=model.task_id,
    )


class MemberTaskRepository(BaseRepository):
    def create(self, member_task: MemberTaskInsert) -> MemberTaskEntity:
        obj = MemberTaskModel(
            member_id=member_task.member_id, task_id=member_task.task_id
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
            raise business.NotFoundById(MemberTaskEntity)

        self._session.delete(obj)
        self._session.flush()
