import re
import typing as t

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


class JumpediaUserAdapter(BaseAdapter[JumpediaUser]):
    jumpedia: JumpediaAdapter

    @property
    def name(self) -> str:
        return self._s.user_name

    @property
    def jumpedia_rank(self) -> JumpediaRank:
        return self._s.jumpedia_rank


class CommunityUserAdapter(BaseAdapter[CommunityUser]):
    _s: CommunityUser

    community: CommunityAdapter
    jumpedia_user: JumpediaUserAdapter

    @property
    def community_rank(self) -> CommunityRank:
        return self._s.community_rank

    @property
    def most_powerful_rank(self) -> JumpediaRank | CommunityRank:
        return self._s.jumpedia_user.jumpedia_rank or self.community_rank

    def get_list_or_default(self, list: str | None) -> ListAdapter:
        if list is not None:
            return self.community.get_list(list)

        list_s = self._s.get_selected_list()

        if list_s is not None:
            return ListAdapter(list_s, self.community)

        return self.community.get_default_selected_list()
