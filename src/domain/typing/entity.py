from domain.entities.attribute import AttributeEntity
from domain.entities.community import CommunityEntity
from domain.entities.list import ListEntity
from domain.entities.member import MemberEntity
from domain.entities.task import TaskEntity
from domain.entities.user import UserEntity

type NamedEntityT = (
    AttributeEntity
    | CommunityEntity
    | ListEntity
    | MemberEntity
    | TaskEntity
    | UserEntity
)
