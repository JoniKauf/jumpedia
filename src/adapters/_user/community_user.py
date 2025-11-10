import typing as t

from src.discord_.errors import FeedbackError
from src.structures.community import CommunityUser
from src.structures.user.rank import CommunityRank, JumpediaRank

from .. import BaseAdapter
from .jumpedia_user import JumpediaUserAdapter

if t.TYPE_CHECKING:
    from .._community import CommunityAdapter
    from .._list import ListAdapter


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
                t"Neither the user `{self.jumpedia_user.name}`, nor the community `{self.community.name}` have a default selected list!"
            )

        return ListAdapter(list, self.community)

