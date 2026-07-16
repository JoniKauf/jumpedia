from dataclasses import dataclass

from domain.types.member import MemberID
from domain.types.task import TaskID


@dataclass(frozen=True, slots=True)
class MemberTaskInsert:
    member_id: MemberID
    task_id: TaskID
    given_by: MemberID