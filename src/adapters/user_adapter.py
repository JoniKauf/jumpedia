

from typing import Any
from adapters.base_adapter import BaseAdapter
from adapters.community_adapter import _CommunityAdapter
from adapters.jumpedia_adapter import JumpediaAdapter
from adapters.list_adapter import _ListAdapter
from errors.feedback import feedbacks
from structures.user import User
from utils import functools2



class _UserAdapter(BaseAdapter[User]):
    def get_best_selected_list(self, community: _CommunityAdapter) -> _ListAdapter:
        list = (
            self._structure.get_selected_list(community._structure)
            or community._structure.get_default_selected_list()
        )

        if list is not None:
            return _ListAdapter(self._interaction, list)
        
        raise feedbacks.temp("Neither you, nor the community you are in has a default list selected.")