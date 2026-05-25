


from dataclasses import dataclass

from services.attribute import AttributeService
from services.community import CommunityService
from services.list import ListService
from services.user import CommunityUserService, UserService


@dataclass(frozen=True)
class Services:
    user: UserService
    community_user: CommunityUserService
    community: CommunityService
    list: ListService
    attribute: AttributeService
