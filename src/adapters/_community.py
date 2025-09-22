


from typing import TYPE_CHECKING, Any, overload
from adapters import BaseAdapter
from adapters._list import ListAdapter
from adapters._user.community_user import CommunityUserAdapter
from adapters._user.jumpedia_user import JumpediaUserAdapter
from errors.feedback import feedbacks
from ranks.community_rank import CommunityRank
from structures.community import Community
from structures.list import List
from utils import text

if TYPE_CHECKING:
    from adapters._jumpedia import JumpediaAdapter
    
def _require_list_with_name(name: text.NormStr, community: Community) -> List:
    list = community.get_list_by_name(name)

    if list is None:
        raise feedbacks.temp(f"List with the name `{name}` could not be found!")
    
    return list

class CommunityAdapter(BaseAdapter):
    _community: Community
    jumpedia: JumpediaAdapter

    @property
    def name(self) -> str:
        return self._community.real_name

    # --- List ---

    def get_lists(self) -> list[ListAdapter]:
        return [
            ListAdapter(list, self)
            for list in
            self._community.get_lists()
        ]
    
    def get_list(self, name: str) -> ListAdapter:
        return ListAdapter(
            _require_list_with_name(text.raw_to_norm(name), self._community), 
            self
        )
    
    def create_list(self, name: str) -> ListAdapter:
        return ListAdapter(self._community.create_list(name), self)
    
    def delete_list(self, name: str) -> None:
        list = _require_list_with_name(text.raw_to_norm(name), self._community)

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
                text.raw_to_norm(name), self._community
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