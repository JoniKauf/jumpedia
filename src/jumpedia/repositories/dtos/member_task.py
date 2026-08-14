from dataclasses import dataclass

from jumpedia.db.models import ListID
from jumpedia.domain.typing.member import MemberID
from jumpedia.domain.typing.task import TaskID


@dataclass(frozen=True, slots=True)
class MemberTaskInsert:
    member_id: MemberID
    list_id: ListID
    task_id: TaskID
    given_by: MemberID
