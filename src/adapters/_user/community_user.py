from dataclasses import dataclass
from typing import TYPE_CHECKING
from adapters import BaseAdapter
from adapters._user.jumpedia_user import JumpediaUserAdapter
from errors.feedback import feedbacks
from ranks.community_rank import CommunityRank
from ranks.jumpedia_rank import JumpediaRank
from structures.user.community_user import CommunityUser

if TYPE_CHECKING:
    from adapters._community import CommunityAdapter
    from adapters._list import ListAdapter


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
            raise feedbacks.temp("No list selected")

        return ListAdapter(list, self.community)

    def get_selected_list_or_default(self) -> ListAdapter:
        list = (
            self._community_user.get_selected_list()
            or self._community_user.community.get_default_selected_list()
        )

        if list is None:
            raise feedbacks.temp(
                "Neither you, nor the community you are in has a default list selected."
            )

        return ListAdapter(list, self.community)
