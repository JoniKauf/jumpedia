from domain.entities.base import BaseEntity
from domain.types.member import MemberID
from domain.types.member_task import MemberTaskID
from domain.types.task import TaskID


class MemberTaskEntity(BaseEntity[MemberTaskID]):
    def __init__(
        self, member_task_id: MemberTaskID, member_id: MemberID, task_id: TaskID
    ) -> None:
        super().__init__(member_task_id)
        self._member_id = member_id
        self._task_id = task_id

    @property
    def member_task_id(self) -> MemberTaskID:
        return self._composite_key[0]

    @property
    def member_id(self) -> MemberID:
        return self._member_id

    @property
    def task_id(self) -> TaskID:
        return self._task_id
