from domain.entities.member import MemberEntity
from domain.entities.member_task import MemberTaskEntity
from domain.entities.task import TaskEntity
from domain.errors.internal import dataclass
from domain.typing.attribute import AnyAttributeTypeT
from domain.typing.field_mapping import FrozenFieldMappingEntityToStrings


@dataclass(frozen=True, slots=True)
class MemberTaskInfo:
    task: TaskEntity
    member_task: MemberTaskEntity
    member: MemberEntity
    data: FrozenFieldMappingEntityToStrings[AnyAttributeTypeT]
