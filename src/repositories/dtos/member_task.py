from dataclasses import dataclass

from domain.typing.member import MemberID
from domain.typing.task import TaskID


@dataclass(frozen=True, slots=True)
class MemberTaskInsert:
    member_id: MemberID
    task_id: TaskID
    given_by: MemberID
