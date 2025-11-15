import re
import typing as t

from discord_.errors import FeedbackError
from structures.community import CommunityUser, JumpediaUser
from structures.user import MAX_ID, MIN_ID
from structures.user.rank import CommunityRank, JumpediaRank

from . import BaseAdapter

if t.TYPE_CHECKING:
    from ._community import CommunityAdapter
    from ._jumpedia import JumpediaAdapter
    from ._list import ListAdapter


MENTION_PATTERN = re.compile(r"^<@([0-9]{0,20})>$")


def _int_to_id(i: int) -> int:
    if MIN_ID > i > MAX_ID:
        raise ValueError("Out of range")

    return i


def _str_to_id(s: str) -> int:
    try:
        identifier = int(s)
    except ValueError:
        pass
    else:
        return _int_to_id(identifier)

    s = s.strip()

    match = MENTION_PATTERN.match(s)

    if not match:
        raise ValueError

    return int(match.group(1))


def identifier_to_id(identifier: str | int) -> int:
    if isinstance(identifier, int):
        return _int_to_id(identifier)

    return _str_to_id(identifier)






class JumpediaUserAdapter(BaseAdapter):
    _jumpedia_user: JumpediaUser

    jumpedia: JumpediaAdapter

    @property
    def name(self) -> str:
        return self._jumpedia_user.user_name

    @property
    def jumpedia_rank(self) -> JumpediaRank:
        return self._jumpedia_user.jumpedia_rank





class CommunityUserAdapter(BaseAdapter):
    _community_user: CommunityUser

    community: CommunityAdapter
    jumpedia_user: JumpediaUserAdapter

    @property
    def community_rank(self) -> CommunityRank:
        return self._community_user.community_rank

    @property
    def most_important_rank(self) -> JumpediaRank | CommunityRank:
        return self._community_user.jumpedia_user.jumpedia_rank or self.community_rank

    def get_selected_list(self) -> ListAdapter:
        list = self._community_user.get_selected_list()

        if list is None:
            raise FeedbackError(
                "No Default Selected List",
                t"Neither the user `{self.jumpedia_user.name}`, nor the community `{self.community.name}` have a default selected list!",
            )

        return ListAdapter(list, self.community)
