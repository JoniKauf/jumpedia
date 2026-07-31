from jumpedia.domain.entities.attribute import AttributeEntity
from jumpedia.domain.entities.community import CommunityEntity
from jumpedia.domain.entities.list import ListEntity
from jumpedia.domain.entities.member import MemberEntity
from jumpedia.domain.entities.task import TaskEntity
from jumpedia.domain.entities.user import UserEntity

type NamedEntityT = (
    AttributeEntity
    | CommunityEntity
    | ListEntity
    | MemberEntity
    | TaskEntity
    | UserEntity
)
