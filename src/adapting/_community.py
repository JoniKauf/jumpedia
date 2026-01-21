import typing as t
from functools import cached_property

from dc_utils import errors, message
from dc_utils.rank import CommunityRank
from structures.community import Community
from structures.errors import StructureCountLimitReachedError, SynsAlreadyTakenError
from structures.list import List
from utils import orm, text

from . import BaseStructureAdapter
from ._list import ListAdapter
from ._user import CommunityUserAdapter, JumpediaUserAdapter

if t.TYPE_CHECKING:
    from ._jumpedia import JumpediaAdapter


def _require_list_with_name(c: orm.Cursor, name: str, community: Community) -> List:
    tup = community.get_list_by_name(c, text.NormStr(name))

    if tup is None:
        raise errors.StructureNotFoundViaSyn(name, List, True)

    return tup[0]


class CommunityAdapter(BaseStructureAdapter[Community]):
    jumpedia: JumpediaAdapter

    @cached_property
    def _c(self) -> orm.Cursor:
        return self.jumpedia._c

    @property
    def name(self) -> text.RealStr:
        return self._o.real_name

    # --- List ---

    def get_lists(self) -> list[ListAdapter]:
        return [ListAdapter(list, self) for list in self._o.get_lists(self._c)]

    def get_list(self, name: str) -> ListAdapter:
        return ListAdapter(_require_list_with_name(self._c, name, self._o), self)

    def create_list(self, name: str) -> ListAdapter:
        try:
            list = self._o.create_list(self._c, text.RealStr(name))
        except SynsAlreadyTakenError as e:
            raise errors.SynsAlreadyTaken(e)
        except StructureCountLimitReachedError as e:
            raise errors.StructureCountLimitReached(e)

        return ListAdapter(list, self)

    def delete_list(self, name: str) -> None:
        list = _require_list_with_name(self._c, name, self._o)
        self._o.delete_list(self._c, list.id)

    @t.overload
    def get_default_selected_list(self) -> ListAdapter:
        pass

    @t.overload
    def get_default_selected_list[T](self, default: T) -> ListAdapter | T:
        pass

    _MISSING = object()

    def get_default_selected_list[T](self, default: T = _MISSING) -> ListAdapter | T:
        list = self._o.get_default_selected_list(self._c)

        if list is None:
            if default is not self.__class__._MISSING:
                return default

            raise errors.FeedbackError(
                "No Default Selected List",
                t"The community {self.name:,} has no default selected list!",
                additional=t"Please specify the list you want to use in the command.",
            )

        return ListAdapter(list, self)

    def set_default_selected_list(self, name: str | None) -> None:
        if name is None:
            list_id = None
        else:
            list_id = _require_list_with_name(self._c, name, self._o).id

        curr_default_selected_list = self.get_default_selected_list(None)

        if curr_default_selected_list is None and list_id is None:
            raise errors.FeedbackError(
                "Already No Default Selected List",
                t"There is already no default selected list!",
                additional=(
                    t"You tried to unset the default selected list "
                    + t"of the community by not entering a list's name "
                    + t"into the command, but there is already no "
                    + t"list selected as the default, therefore "
                    + t"nothing changed."
                ),
                explicit_message_status=message.MessageStatus.WARNING,
            )

        if (
            curr_default_selected_list is not None
            and list_id == curr_default_selected_list._o.id
        ):
            raise errors.FeedbackError(
                "Already Specified Default Selected List",
                t"The specified list is already the default selected list, therefore nothing changed!",
            )

        self._o.set_default_selected_list(self._c, list_id)

    # --- User ---

    def get_or_create_community_user(
        self,
        jumpedia_user: JumpediaUserAdapter,
        *,
        override_community_rank: CommunityRank | None = None,
    ) -> CommunityUserAdapter:
        return CommunityUserAdapter(
            self._o.get_or_create_community_user(
                self._c,
                jumpedia_user._o,
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
        return len(self._o.get_server_ids(self._c))
