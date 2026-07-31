from jumpedia.domain.entities.base import BaseEntity

lazy from jumpedia.domain.typing.member import MemberID
from jumpedia.domain.typing.member_task import MemberTaskID

lazy from jumpedia.domain.typing.task import TaskID
lazy from jumpedia.domain.value_objects.datetime import DateTimeWrapper
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MemberTaskEntity(BaseEntity[MemberTaskID]):
    member_id: MemberID
    task_id: TaskID
    given_at: DateTimeWrapper
    given_by: MemberID | None

    @property
    def member_task_id(self) -> MemberTaskID:
        return self.key[0]
