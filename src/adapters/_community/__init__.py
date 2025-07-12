

from dataclasses import dataclass
from typing import Any, overload
from adapters._base_adapter import BaseAdapter
from adapters._list import ListAdapter
from adapters._users.community_user import CommunityUserAdapter
from adapters._users.jumpedia_user import JumpediaUserAdapter
from adapters._jumpedia import JumpediaAdapter
from discordtools import users
from errors.feedback import FeedbackError, feedbacks
from ranks.community_rank import CommunityRank
from structures.community import Community
from structures import list as list_
from structures.list import List
from structures.user.community_user import CommunityUser
from structures.user.jumpedia_user import JumpediaUser


def _require_list_with_name(name: str, community: Community) -> List:
    list = community.get_list_by_name(name)

    if list is None:
        raise feedbacks.temp(f"List with the name `{name}` could not be found!")
    
    return list

def _valnitize_list_name(name: str) -> str:
    from utils import text

    return text.valnitize(
        name, 
        list_.MIN_NAME_LENGTH, 
        list_.MAX_NAME_LENGTH
    )

@dataclass(frozen=True)
class CommunityAdapter(BaseAdapter):
    _community: Community

    jumpedia: JumpediaAdapter

    @property
    def name(self) -> str:
        return self._community.name

    # --- List ---

    def get_lists(self) -> list[ListAdapter]:
        return [
            ListAdapter(list, self)
            for list in
            self._community.get_lists()
        ]
    
    def get_list(self, name: str) -> ListAdapter:
        return ListAdapter(
            _require_list_with_name(_valnitize_list_name(name), self._community), 
            self
        )
    
    def create_list(self, name: str) -> ListAdapter:
        from utils import text

        name = _valnitize_list_name(name)
        
        return ListAdapter(self._community.create_list(name), self)
    
    def delete_list(self, name: str) -> None:
        list = _require_list_with_name(_valnitize_list_name(name), self._community)

        if not self._community.delete_list(list.id):
            raise feedbacks.temp("The community or list was just deleted!")
    
    @overload
    def get_default_selected_list(self, name: str) -> ListAdapter:
        pass
        
    @overload
    def get_default_selected_list[T](self, name: str, default: T) -> ListAdapter | T:
        pass

    _MISSING = object()

    def get_default_selected_list(self, name: str, default: Any = _MISSING):
        name = _valnitize_list_name(name)

        list = self._community.get_default_selected_list()

        if list is None:
            if default is not self.__class__._MISSING:
                return default
            
            raise feedbacks.temp("No default selected list on server")
        
        return name
        
        
    def set_default_selected_list(self, name: str | None) -> None:
        if name is None:
            list_id = None
        else:
            list_id = _require_list_with_name(
                _valnitize_list_name(name), self._community
            ).id
        
        if not self._community.set_default_selected_list(list_id):
            raise feedbacks.temp("The specified list or community was just deleted!")
    

    # --- User ---
    
    def get_or_create_community_user(self, jumpedia_user: JumpediaUserAdapter, override_community_rank: CommunityRank | None = None) -> CommunityUserAdapter:
        return CommunityUserAdapter(self._community.get_or_create_community_user(
            jumpedia_user._jumpedia_user,
            override_community_rank or CommunityRank.DEFAULT,
            None,
            override_community_rank is not None,
            False
        ), self, jumpedia_user)
    
    def get_or_create_current_community_user(self, override_community_rank: CommunityRank | None = None) -> CommunityUserAdapter:
        return self.get_or_create_community_user(
            self.jumpedia.get_or_create_current_jumpedia_user(),
            override_community_rank
        )