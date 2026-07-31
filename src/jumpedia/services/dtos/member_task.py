from jumpedia.domain.entities.member import MemberEntity
from jumpedia.domain.entities.member_task import MemberTaskEntity
from jumpedia.domain.entities.task import TaskEntity
from jumpedia.domain.errors.internal import dataclass
from jumpedia.domain.typing.attribute import AnyAttributeTypeT
from jumpedia.domain.typing.field_mapping import FrozenFieldMappingEntityToStrings


@dataclass(frozen=True, slots=True)
class MemberTaskInfo:
    task: TaskEntity
    member_task: MemberTaskEntity
    member: MemberEntity
    data: FrozenFieldMappingEntityToStrings[AnyAttributeTypeT]
