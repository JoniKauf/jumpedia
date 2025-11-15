import typing as t

from discord_.errors import FeedbackError
from structures.community import Community
from structures.list import List
from structures.user.rank import CommunityRank
from utils import text

from . import BaseAdapter, errors
from ._list import ListAdapter
from ._user import CommunityUserAdapter, JumpediaUserAdapter

if t.TYPE_CHECKING:
    from ._jumpedia import JumpediaAdapter


def _require_list_with_name(name: text.NormStr, community: Community) -> List:
    list = community.get_list_by_name(name)

    if list is None:
        raise errors.StructureNotFoundViaSynFeedbackError(name, List, True)

    return list


class CommunityAdapter(BaseAdapter):
    _community: Community
    jumpedia: JumpediaAdapter

    @property
    def name(self) -> text.RealStr:
        return self._community.real_name

    # --- List ---

    def get_lists(self) -> list[ListAdapter]:
        return [ListAdapter(list, self) for list in self._community.get_lists()]

    def get_list(self, name: str) -> ListAdapter:
        return ListAdapter(
            _require_list_with_name(text.NormStr(name), self._community), self
        )

    def create_list(self, name: str) -> ListAdapter:
        return ListAdapter(self._community.create_list(text.RealStr(name)), self)

    def delete_list(self, name: str) -> None:
        list = _require_list_with_name(text.NormStr(name), self._community)
        self._community.delete_list(list.id)

    @t.overload
    def get_default_selected_list(self) -> ListAdapter:
        pass

    @t.overload
    def get_default_selected_list[T](self, default: T) -> ListAdapter | T:
        pass

    _MISSING = object()

    def get_default_selected_list[T](self, default: T = _MISSING) -> ListAdapter | T:
        list = self._community.get_default_selected_list()

        if list is None:
            if default is not self.__class__._MISSING:
                return default

            raise FeedbackError(
                "No Default Selected List",
                t"The community `{self.name}` has no default selected list!",
            )

        return ListAdapter(list, self)

    def set_default_selected_list(self, name: str | None) -> None:
        if name is None:
            list_id = None
        else:
            list_id = _require_list_with_name(text.NormStr(name), self._community).id

        self._community.set_default_selected_list(list_id)

    # --- User ---

    def get_or_create_community_user(
        self,
        jumpedia_user: JumpediaUserAdapter,
        override_community_rank: CommunityRank | None = None,
    ) -> CommunityUserAdapter:
        return CommunityUserAdapter(
            self._community.get_or_create_community_user(
                jumpedia_user._jumpedia_user,
                override_community_rank or CommunityRank.DEFAULT,
                None,
                override_community_rank is not None,
                False,
            ),
            self,
            jumpedia_user,
        )

    def get_or_create_current_community_user(
        self, override_community_rank: CommunityRank | None = None
    ) -> CommunityUserAdapter:
        return self.get_or_create_community_user(
            self.jumpedia.get_or_create_current_jumpedia_user(), override_community_rank
        )

    # --- Server ---

    def get_server_count(self) -> int:
        return len(self._community.get_server_ids())
