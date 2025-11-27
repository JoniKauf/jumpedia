import typing as t
from functools import cached_property

import discord as dc

from adapters._server import ServerAdapter
from discord_.errors import FeedbackError
from discord_.utils_ import messaging
from structures.community import CommunityUser, JumpediaUser
from structures.list import List
from utils import text
from utils.rank import CommunityRank, JumpediaRank, ServerRank

from . import BaseAdapter, BaseStructureAdapter, errors

if t.TYPE_CHECKING:
    from ._community import CommunityAdapter
    from ._jumpedia import JumpediaAdapter
    from ._list import ListAdapter
    from .interaction import InteractionAdapter


def _get_set_own_rank_error(
    executing_user: JumpediaUserAdapter | CommunityUserAdapter,
    set_user: JumpediaUserAdapter | CommunityUserAdapter,
) -> FeedbackError | None:
    if set_user == executing_user and not executing_user.jumpedia_rank:
        return FeedbackError(
            "Cannot Set Own Rank",
            t"You cannot set your own rank!",
            additional=t"Only somebody with a rank higher than yours can set your rank.",
        )

    return None


@t.overload
def _get_set_rank_error(
    executing_user: CommunityUserAdapter,
    set_user: CommunityUserAdapter,
    rank: CommunityRank,
) -> FeedbackError | None:
    pass


@t.overload
def _get_set_rank_error(
    executing_user: JumpediaUserAdapter,
    set_user: JumpediaUserAdapter,
    rank: JumpediaRank,
) -> FeedbackError | None:
    pass


def _get_set_rank_error(
    executing_user: JumpediaUserAdapter | CommunityUserAdapter,
    set_user: JumpediaUserAdapter | CommunityUserAdapter,
    rank: JumpediaRank | CommunityRank,
) -> FeedbackError | None:
    err = _get_set_own_rank_error(executing_user, set_user)

    if err is not None:
        return err

    executing_best_rank: JumpediaRank | CommunityRank
    set_best_rank: JumpediaRank | CommunityRank

    if isinstance(executing_user, JumpediaUserAdapter):
        assert isinstance(set_user, JumpediaUserAdapter)
        assert isinstance(rank, JumpediaRank)

        executing_best_rank = executing_user.jumpedia_rank
        set_best_rank = set_user.jumpedia_rank

    else:
        assert isinstance(set_user, CommunityUserAdapter)
        assert isinstance(rank, CommunityRank)

        executing_best_rank = executing_user.most_powerful_rank
        set_best_rank = set_user.most_powerful_rank

    if executing_best_rank <= set_best_rank:
        return FeedbackError(
            "Cannot Set Rank Of More Powerful User",
            t"You cannot set the rank of a user more powerful than you!",
            additional=(
                t"The user `{set_user}` has the "
                t"{set_best_rank.mention()}, "
                t"but you have the less powerful "
                t"{executing_best_rank.mention()}."
            ),
        )

    if rank >= executing_best_rank:
        return FeedbackError(
            "Cannot Set Rank Of Own Power Or Higher",
            t"You cannot set the rank of a user to a rank that is equally or more powerful than yours!",
            additional=(
                t"The {rank.mention()} "
                t"you are trying set for `{set_user}` is equally or more powerful "
                t"than your {executing_best_rank.mention()}."
            ),
        )

    if (
        isinstance(set_user, JumpediaUserAdapter) and rank is set_user.jumpedia_rank
    ) or (
        isinstance(set_user, CommunityUserAdapter) and rank is set_user.community_rank
    ):
        return FeedbackError(
            "User Already Has Specified Rank",
            t"The user `{set_user}` already has the {rank.mention()}, therefore nothing changed!",
            explicit_message_status=messaging.MessageStatus.WARNING,
        )

    return None


@t.overload
def get_success_msg(set_user: JumpediaUserAdapter, rank: JumpediaRank):
    pass


@t.overload
def get_success_msg(set_user: CommunityUserAdapter, rank: CommunityRank):
    pass


def get_success_msg(
    set_user: JumpediaUserAdapter | CommunityUserAdapter,
    rank: JumpediaRank | CommunityRank,
):
    return messaging.layout(
        f"{rank.__class__.type_name.title()} Set",
        t"The jumpedia rank of `{set_user}` has successfully been set to `{rank}`!",
        message_status=messaging.MessageStatus.SUCCESS,
    )


class JumpediaUserAdapter(BaseStructureAdapter[JumpediaUser]):
    jumpedia: JumpediaAdapter

    @property
    def name(self) -> str:
        return self._s.user_name

    @property
    def jumpedia_rank(self) -> JumpediaRank:
        return self._s.jumpedia_rank

    def set_jumpedia_rank(
        self, jumpedia_rank: JumpediaRank, executing_jumpedia_user: JumpediaUserAdapter
    ) -> str:
        error = _get_set_rank_error(executing_jumpedia_user, self, jumpedia_rank)

        if error is not None:
            raise error

        _ = self.jumpedia._s.get_or_create_jumpedia_user(
            self._s.id,
            self.name,
            jumpedia_rank,
            override_name_if_user_exists=False,
            override_jumpedia_rank_if_user_exists=True,
        )

        return get_success_msg(self, jumpedia_rank)


class CommunityUserAdapter(BaseStructureAdapter[CommunityUser]):
    _s: CommunityUser

    community: CommunityAdapter
    jumpedia_user: JumpediaUserAdapter

    @property
    def name(self) -> str:
        return self.jumpedia_user.name

    @property
    def community_rank(self) -> CommunityRank:
        return self._s.community_rank

    @property
    def jumpedia_rank(self) -> JumpediaRank:
        return self.jumpedia_user.jumpedia_rank

    @property
    def most_powerful_rank(self) -> JumpediaRank | CommunityRank:
        return self._s.jumpedia_user.jumpedia_rank or self.community_rank

    def get_selected_list(self) -> ListAdapter | None:
        from ._list import ListAdapter

        list_s = self._s.get_selected_list()

        if list_s is None:
            return None

        return ListAdapter(list_s, self.community)

    def get_selected_list_or_default(self, list: str | None) -> ListAdapter:
        if list is not None:
            return self.community.get_list(list)

        list_obj = self.get_selected_list()

        if list_obj is not None:
            return list_obj

        return self.community.get_default_selected_list()

    def set_community_rank(
        self,
        community_rank: CommunityRank,
        executing_community_user: CommunityUserAdapter,
    ) -> str:
        assert self.community == executing_community_user.community

        error = _get_set_rank_error(executing_community_user, self, community_rank)

        if error is not None:
            raise error

        _ = self.community._s.get_or_create_community_user(
            self.jumpedia_user._s,
            community_rank,
            None,
            override_community_rank_if_user_exists=True,
            override_selected_list_if_user_exists=False,
        )

        return get_success_msg(self, community_rank)

    def set_selected_list(
        self, list: str | None, executing_community_user: CommunityUserAdapter
    ) -> ListAdapter | None:
        assert self.community == executing_community_user.community

        from . import _community
        from ._list import ListAdapter

        REQ_RANK = CommunityRank.MODERATOR

        if (
            self != executing_community_user
            and executing_community_user.most_powerful_rank.value < REQ_RANK.value
        ):
            raise errors.NotEnoughPowerToAffectOtherUsersFeedbackError(
                executing_community_user.most_powerful_rank, REQ_RANK
            )

        selected_list: ListAdapter | None

        if list is None:
            selected_list = None
        else:
            selected_list = ListAdapter(
                _community._require_list_with_name(
                    text.NormStr(list), self.community._s
                ),
                self.community,
            )

        if self.get_selected_list() == selected_list:
            start = (
                "You already have"
                if self == executing_community_user
                else f"The user `{self}` already has"
            )
            selection = (
                "no selected list"
                if selected_list is None
                else f"the selected list `{selected_list}`"
            )

            raise FeedbackError(
                "User Already Has Specified Selected List Set",
                t"{start} {selection} set, therefore nothing changed!",
                explicit_message_status=messaging.MessageStatus.WARNING,
            )

        self._s.set_selected_list(
            None if selected_list is None else selected_list._s.id
        )

        return selected_list

    def transfer_ownership(
        self, executing_community_user: CommunityUserAdapter
    ) -> None:
        assert self.community == executing_community_user.community

        err = _get_set_own_rank_error(self, executing_community_user)

        if err is not None:
            raise err

        if executing_community_user.community_rank != CommunityRank.OWNER:
            raise FeedbackError(
                "Not Owner",
                t"You are not an owner of this community, so you cannot transfer ownership!",
            )

        old_rank = self.community_rank

        try:
            executing_community_user.community.get_or_create_community_user(
                executing_community_user.jumpedia_user,
                override_community_rank=CommunityRank.ADMINISTRATOR,
            )
            self.community.get_or_create_community_user(
                self.jumpedia_user, override_community_rank=CommunityRank.OWNER
            )
        except BaseException as e:
            executing_community_user.community.get_or_create_community_user(
                executing_community_user.jumpedia_user,
                override_community_rank=CommunityRank.OWNER,
            )
            self.community.get_or_create_community_user(
                self.jumpedia_user, override_community_rank=old_rank
            )

            raise e


class ServerUserAdapter(BaseAdapter[dc.User]):
    interaction: InteractionAdapter

    @property
    def id(self) -> int:
        return self._s.id

    @property
    def name(self) -> str:
        return self._s.global_name or self._s.name


class ServerMemberAdapter(BaseAdapter[dc.Member]):
    server: ServerAdapter
    user: ServerUserAdapter

    @cached_property
    def server_rank(self) -> ServerRank:
        if self._s == self.server._s.owner:
            return ServerRank.OWNER

        if self._s.guild_permissions.administrator:
            return ServerRank.ADMINISTRATOR

        return ServerRank.USER
