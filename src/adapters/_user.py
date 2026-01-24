import typing as t
from functools import cached_property

import discord as dc

import dc_utils
from adapters._server import ServerAdapter
from dc_utils import errors, message
from structures.community import CommunityUser, JumpediaUser
from utils import orm, text
from utils.rank import CommunityRank, JumpediaRank, ServerRank

from . import BaseAdapter, BaseStructureAdapter

if t.TYPE_CHECKING:
    from ._community import CommunityAdapter
    from ._jumpedia import JumpediaAdapter
    from ._list import ListAdapter
    from .interaction import InteractionAdapter


def _get_set_own_rank_error(
    ia_user: JumpediaUserAdapter | CommunityUserAdapter,
    set_user: JumpediaUserAdapter | CommunityUserAdapter,
) -> errors.FeedbackError | None:
    if set_user == ia_user and not ia_user.jumpedia_rank:
        return errors.FeedbackError(
            "Cannot Set Own Rank",
            t"You cannot set your own rank!",
            additional=t"Only somebody with a rank higher than yours can set your rank.",
        )

    return None


@t.overload
def _get_set_rank_error(
    ia_user: CommunityUserAdapter,
    set_user: CommunityUserAdapter,
    rank: CommunityRank,
) -> errors.FeedbackError | None:
    pass


@t.overload
def _get_set_rank_error(
    ia_user: JumpediaUserAdapter,
    set_user: JumpediaUserAdapter,
    rank: JumpediaRank,
) -> errors.FeedbackError | None:
    pass


def _get_set_rank_error(
    ia_user: JumpediaUserAdapter | CommunityUserAdapter,
    set_user: JumpediaUserAdapter | CommunityUserAdapter,
    rank: JumpediaRank | CommunityRank,
) -> errors.FeedbackError | None:
    err = _get_set_own_rank_error(ia_user, set_user)

    if err is not None:
        return err

    ia_best_rank: JumpediaRank | CommunityRank
    set_best_rank: JumpediaRank | CommunityRank

    if isinstance(ia_user, JumpediaUserAdapter):
        assert isinstance(set_user, JumpediaUserAdapter)
        assert isinstance(rank, JumpediaRank)

        ia_best_rank = ia_user.jumpedia_rank
        set_best_rank = set_user.jumpedia_rank

    else:
        assert isinstance(set_user, CommunityUserAdapter)
        assert isinstance(rank, CommunityRank)

        ia_best_rank = ia_user.most_powerful_rank
        set_best_rank = set_user.most_powerful_rank

    if ia_best_rank <= set_best_rank:
        return errors.FeedbackError(
            "Cannot Set Rank Of More Powerful User",
            t"You cannot set the rank of a user more powerful than you!",
            additional=(
                t"The user {set_user:,} has the "
                + set_best_rank.mention()
                + t", but you have the less powerful "
                + ia_best_rank.mention()
                + t"."
            ),
        )

    if rank >= ia_best_rank:
        return errors.FeedbackError(
            "Cannot Set Rank Of Own Power Or Higher",
            t"You cannot set the rank of a user to a rank that is equally or more powerful than yours!",
            additional=(
                t"The "
                + rank.mention()
                + t"you are trying set for {set_user:,} is equally or more powerful "
                t"than your " + ia_best_rank.mention() + t"."
            ),
        )

    if (
        isinstance(set_user, JumpediaUserAdapter) and rank is set_user.jumpedia_rank
    ) or (
        isinstance(set_user, CommunityUserAdapter) and rank is set_user.community_rank
    ):
        return errors.FeedbackError(
            "User Already Has Specified Rank",
            t"The user {set_user:,} already has the {rank.mention()}, therefore nothing changed!",
            explicit_message_status=message.MessageStatus.WARNING,
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
    return message.layout(
        f"{rank.__class__.type_name.title()} Set",
        t"The jumpedia rank of {set_user:,} has successfully been set to {rank:,}!",
        message_status=message.MessageStatus.SUCCESS,
    )


class UserAdapter(BaseAdapter[dc.User]):
    interaction: InteractionAdapter
    _member: None | dc.Member = None

    @cached_property
    def _c(self) -> orm.Cursor:
        return self.interaction._c

    @property
    def id(self) -> int:
        return self._o.id

    @property
    def name(self) -> str:
        return self._o.global_name or self._o.name

    # Cached property bec we want the same obj and it's simple
    @cached_property
    def try_as_member(self) -> ServerMemberAdapter:
        if self._member is None:
            raise errors.FeedbackError(
                "Not On Server", t"You must execute this command on a server!"
            )

        return ServerMemberAdapter(
            self._member, ServerAdapter(self._member.guild, self.interaction), self
        )

    @cached_property
    def is_interacting_user(self) -> bool:
        return self.id == self.interaction.ia_user.id


class ServerMemberAdapter(BaseAdapter[dc.Member]):
    server: ServerAdapter
    user: UserAdapter

    @cached_property
    def _c(self) -> orm.Cursor:
        return self.server._c

    @cached_property
    def server_rank(self) -> ServerRank:
        if self._o == self.server._o.owner:
            return ServerRank.OWNER

        if self._o.guild_permissions.administrator:
            return ServerRank.ADMINISTRATOR

        return ServerRank.USER

    @property
    def id(self) -> int:
        return self.user.id

    @property
    def name(self) -> str:
        return self.user.name


class JumpediaUserAdapter(BaseStructureAdapter[JumpediaUser]):
    jumpedia: JumpediaAdapter
    user: UserAdapter

    @cached_property
    def _c(self) -> orm.Cursor:
        return self.jumpedia._c

    @property
    def name(self) -> str:
        return self._o.user_name

    @property
    def jumpedia_rank(self) -> JumpediaRank:
        return self._o.jumpedia_rank

    def set_jumpedia_rank(self, jumpedia_rank: JumpediaRank) -> str:
        error = _get_set_rank_error(
            self.jumpedia.interaction.ia_jumpedia_user, self, jumpedia_rank
        )

        if error is not None:
            raise error

        _ = self.jumpedia._o.get_or_create_jumpedia_user(
            self._c,
            self._o.id,
            self.name,
            jumpedia_rank,
            override_name_if_user_exists=False,
            override_jumpedia_rank_if_user_exists=True,
        )

        return get_success_msg(self, jumpedia_rank)


class CommunityUserAdapter(BaseStructureAdapter[CommunityUser]):
    community: CommunityAdapter
    jumpedia_user: JumpediaUserAdapter

    @cached_property
    def _c(self) -> orm.Cursor:
        return self.community._c

    @property
    def name(self) -> str:
        return self.jumpedia_user.name

    @cached_property
    def server_member(self) -> ServerMemberAdapter:
        return self.jumpedia_user.user.try_as_member

    @cached_property
    def server_rank(self) -> ServerRank:
        return self.server_member.server_rank

    @property
    def community_rank(self) -> CommunityRank:
        return self._o.community_rank

    @property
    def jumpedia_rank(self) -> JumpediaRank:
        return self.jumpedia_user.jumpedia_rank

    @cached_property
    def most_powerful_rank(self) -> JumpediaRank | CommunityRank:
        return self._o.jumpedia_user.jumpedia_rank or self.community_rank

    def get_selected_list(self) -> ListAdapter | None:
        from ._list import ListAdapter

        list_s = self._o.get_selected_list(self._c)

        if list_s is None:
            return None

        return ListAdapter(list_s, self.community)

    def set_community_rank(
        self,
        community_rank: CommunityRank,
        executing_community_user: CommunityUserAdapter,
    ) -> str:
        assert self.community == executing_community_user.community

        error = _get_set_rank_error(executing_community_user, self, community_rank)

        if error is not None:
            raise error

        _ = self.community._o.get_or_create_community_user(
            self._c,
            self.jumpedia_user._o,
            community_rank,
            None,
            override_community_rank_if_user_exists=True,
            override_selected_list_if_user_exists=False,
        )

        return get_success_msg(self, community_rank)

    def set_selected_list(self, list: str | None) -> ListAdapter | None:
        from . import _community
        from ._list import ListAdapter

        selected_list: ListAdapter | None

        if list is None:
            selected_list = None
        else:
            selected_list = ListAdapter(
                _community._require_list_with_name(
                    self._c, text.RealStr(list), self.community._o
                ),
                self.community,
            )

        if self.get_selected_list() == selected_list:
            selection = (
                t"no selected list"
                if selected_list is None
                else t"the selected list {selected_list:,}"
            )

            raise errors.FeedbackError(
                "User Already Has Specified Selected List Set",
                t"The user {self:,} already has "
                + selection
                + t" set, therefore nothing changed!",
                explicit_message_status=message.MessageStatus.WARNING,
            )

        self._o.set_selected_list(
            self._c, None if selected_list is None else selected_list._o.id
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
            raise errors.FeedbackError(
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
