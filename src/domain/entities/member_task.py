from domain.entities.base import BaseEntity
from domain.typing.member import MemberID
from domain.typing.member_task import MemberTaskID
from domain.typing.task import TaskID
from domain.value_objects.datetime import DateTimeWrapper
from domain.value_objects.member import OptionalMemberWrapper


class MemberTaskEntity(BaseEntity[MemberTaskID]):
    def __init__(
        self,
        member_task_id: MemberTaskID,
        member_id: MemberID,
        task_id: TaskID,
        given_at: DateTimeWrapper,
        given_by: MemberID | None,
    ) -> None:
        super().__init__(member_task_id)
        self._member_id = member_id
        self._task_id = task_id
        self._given_at = given_at
        self._given_by = given_by

    @property
    def member_task_id(self) -> MemberTaskID:
        return self._composite_key[0]

    @property
    def member_id(self) -> MemberID:
        return self._member_id

    @property
    def task_id(self) -> TaskID:
        return self._task_id

    @property
    def given_at(self) -> DateTimeWrapper:
        return self._given_at

    @property
    def given_by(self) -> MemberID | None:
        return self._given_by
