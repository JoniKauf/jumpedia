import typing as t

from discord_.errors import FeedbackError
from discord_.utils_ import messaging
from structures.community import Community
from structures.errors import StructureCountLimitReachedError, SynsAlreadyTakenError
from structures.list import List
from utils import text
from utils.rank import CommunityRank

from . import BaseStructureAdapter, errors
from ._list import ListAdapter
from ._user import CommunityUserAdapter, JumpediaUserAdapter

if t.TYPE_CHECKING:
    from ._jumpedia import JumpediaAdapter


def _require_list_with_name(name: text.NormStr, community: Community) -> List:
    list = community.get_list_by_name(name)

    if list is None:
        raise errors.StructureNotFoundViaSynFeedbackError(name, List, True)

    return list


class CommunityAdapter(BaseStructureAdapter[Community]):
    jumpedia: JumpediaAdapter

    @property
    def name(self) -> text.RealStr:
        return self._s.real_name

    # --- List ---

    def get_lists(self) -> list[ListAdapter]:
        return [ListAdapter(list, self) for list in self._s.get_lists()]

    def get_list(self, name: str) -> ListAdapter:
        return ListAdapter(_require_list_with_name(text.NormStr(name), self._s), self)

    def create_list(self, name: str) -> ListAdapter:
        try:
            list = self._s.create_list(text.RealStr(name))
        except SynsAlreadyTakenError as e:
            raise errors.SynsAlreadyTakenFeedbackError(e)
        except StructureCountLimitReachedError as e:
            raise errors.StructureCountLimitReachedFeedbackError(e)

        return ListAdapter(list, self)

    def delete_list(self, name: str) -> None:
        list = _require_list_with_name(text.NormStr(name), self._s)
        self._s.delete_list(list.id)

    @t.overload
    def get_default_selected_list(self) -> ListAdapter:
        pass

    @t.overload
    def get_default_selected_list[T](self, default: T) -> ListAdapter | T:
        pass

    _MISSING = object()

    def get_default_selected_list[T](self, default: T = _MISSING) -> ListAdapter | T:
        list = self._s.get_default_selected_list()

        if list is None:
            if default is not self.__class__._MISSING:
                return default

            raise FeedbackError(
                "No Default Selected List",
                t"The community {self.name:,} has no default selected list!",
                additional=t"Please specify the list you want to use in the command.",
            )

        return ListAdapter(list, self)

    def set_default_selected_list(self, name: str | None) -> None:
        if name is None:
            list_id = None
        else:
            list_id = _require_list_with_name(text.NormStr(name), self._s).id

        curr_default_selected_list = self.get_default_selected_list(None)

        if curr_default_selected_list is None and list_id is None:
            raise FeedbackError(
                "Already No Default Selected List",
                t"There is already no default selected list!",
                additional=(
                    t"You tried to unset the default selected list "
                    + t"of the community by not entering a list's name "
                    + t"into the command, but there is already no "
                    + t"list selected as the default, therefore "
                    + t"nothing changed."
                ),
                explicit_message_status=messaging.MessageStatus.WARNING,
            )

        if (
            curr_default_selected_list is not None
            and list_id == curr_default_selected_list._s.id
        ):
            raise FeedbackError(
                "Already Specified Default Selected List",
                t"The specified list is already the default selected list, therefore nothing changed!",
            )

        self._s.set_default_selected_list(list_id)

    # --- User ---

    def get_or_create_community_user(
        self,
        jumpedia_user: JumpediaUserAdapter,
        *,
        override_community_rank: CommunityRank | None = None,
    ) -> CommunityUserAdapter:
        return CommunityUserAdapter(
            self._s.get_or_create_community_user(
                jumpedia_user._s,
                override_community_rank or CommunityRank.DEFAULT,
                None,
                override_community_rank is not None,
                False,
            ),
            self,
            jumpedia_user,
        )

    # --- Server ---

    def get_server_count(self) -> int:
        return len(self._s.get_server_ids())
