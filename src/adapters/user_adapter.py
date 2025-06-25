

from typing import Any
from adapters.base_adapter import BaseAdapter
from adapters.list_adapter import _ListAdapter
from structures.user import AnyUserT
from utils import functools2



class _UserAdapter(BaseAdapter[Any]):

    def get_best_selected_list(self) -> _ListAdapter:
        community_user = self..community_user

        if community_user is not None and (list := community_user.selected_list) is not None:
            return list
        
        if (community := self.get_community()) is not None:
            list = community.get_default_selected_list()

            if list is not None:
                return list
        
        raise fbe.TemporaryFeedbackError("Neither you, nor the community you are in has a default list selected.")