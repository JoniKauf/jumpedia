from dataclasses import dataclass

from jumpedia.domain.typing.community import CommunityID
from jumpedia.domain.value_objects.string import Str


@dataclass(frozen=True, slots=True)
class ListInsert:
    community_id: CommunityID
    name: Str
