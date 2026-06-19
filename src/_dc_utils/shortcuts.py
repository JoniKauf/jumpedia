import typing as t

import discord as dc

from _dc_utils import errors
from domain.enum.rank import CommunityRank, JumpediaRank

if t.TYPE_CHECKING:
    from _adapters._community import CommunityAdapter
    from _adapters._jumpedia import JumpediaAdapter
    from _adapters._list import ListAdapter
    from _adapters._user import CommunityUserAdapter, JumpediaUserAdapter, UserAdapter
    from _adapters.interaction import _InteractionAdapter


def _get_jumpedia_and_interaction(
    data: JumpediaAdapter | _InteractionAdapter, /
) -> tuple[_InteractionAdapter, JumpediaAdapter]:
    from _adapters.interaction import _InteractionAdapter

    if isinstance(data, _InteractionAdapter):
        return data, data.jumpedia

    return data.interaction, data


@t.overload
def get_current_community(jumpedia: JumpediaAdapter, /) -> CommunityAdapter:
    pass


@t.overload
def get_current_community(interaction: _InteractionAdapter, /) -> CommunityAdapter:
    pass


def get_current_community(
    data: JumpediaAdapter | _InteractionAdapter, /
) -> CommunityAdapter:
    from _adapters._community import CommunityAdapter

    interaction, jumpedia = _get_jumpedia_and_interaction(data)

    del data

    tup = jumpedia._o.get_community_by_server_id(
        interaction._c, interaction.ia_server.id
    )

    if tup is None:
        raise errors.ServerNotConnectedToACommunity()

    return CommunityAdapter(tup[0], jumpedia)


@t.overload
def get_or_create_specified_or_current_jumpedia_user(
    jumpedia: JumpediaAdapter,
    user: None | dc.User,
    /,
    *,
    override_jumpedia_rank: JumpediaRank | None = None,
) -> JumpediaUserAdapter:
    pass


@t.overload
def get_or_create_specified_or_current_jumpedia_user(
    interaction: _InteractionAdapter,
    user: None | dc.User,
    /,
    *,
    override_jumpedia_rank: JumpediaRank | None = None,
) -> JumpediaUserAdapter:
    pass


def get_or_create_specified_or_current_jumpedia_user(
    data: JumpediaAdapter | _InteractionAdapter,
    user: None | dc.User,
    /,
    *,
    override_jumpedia_rank: JumpediaRank | None = None,
) -> JumpediaUserAdapter:
    from _adapters._jumpedia import JumpediaAdapter
    from _adapters._user import UserAdapter

    jumpedia: JumpediaAdapter = (
        data if isinstance(data, JumpediaAdapter) else data.jumpedia
    )

    del data

    if user is None and override_jumpedia_rank is None:
        return jumpedia.interaction.ia_jumpedia_user

    return jumpedia.get_or_create_jumpedia_user(
        (
            jumpedia.interaction.ia_user
            if user is None
            else UserAdapter(user, jumpedia.interaction)
        ),
        override_jumpedia_rank=override_jumpedia_rank,
    )


@t.overload
def get_or_create_specified_or_current_community_user(
    community: CommunityAdapter,
    user: JumpediaUserAdapter,
    /,
    *,
    override_community_rank: CommunityRank | None = None,
) -> CommunityUserAdapter:
    pass


@t.overload
def get_or_create_specified_or_current_community_user(
    community: CommunityAdapter,
    user: dc.User | None,
    /,
    *,
    override_jumpedia_rank: JumpediaRank | None = None,
    override_community_rank: CommunityRank | None = None,
) -> CommunityUserAdapter:
    pass


@t.overload
def get_or_create_specified_or_current_community_user(
    jumpedia: JumpediaAdapter,
    user: dc.User | None,
    /,
    *,
    override_jumpedia_rank: JumpediaRank | None = None,
    override_community_rank: CommunityRank | None = None,
) -> CommunityUserAdapter:
    pass


@t.overload
def get_or_create_specified_or_current_community_user(
    interaction: _InteractionAdapter,
    user: dc.User | None,
    /,
    *,
    override_jumpedia_rank: JumpediaRank | None = None,
    override_community_rank: CommunityRank | None = None,
) -> CommunityUserAdapter:
    pass


def get_or_create_specified_or_current_community_user(
    data: CommunityAdapter | JumpediaAdapter | _InteractionAdapter,
    user: dc.User | JumpediaUserAdapter | None,
    /,
    *,
    override_jumpedia_rank: JumpediaRank | None = None,
    override_community_rank: CommunityRank | None = None,
) -> CommunityUserAdapter:
    from _adapters._community import CommunityAdapter
    from _adapters._jumpedia import JumpediaAdapter
    from _adapters._user import JumpediaUserAdapter
    from _adapters.interaction import _InteractionAdapter

    if isinstance(user, JumpediaUserAdapter):
        assert isinstance(data, CommunityAdapter)

        return data.get_or_create_community_user(
            user, override_community_rank=override_community_rank
        )

    interaction: _InteractionAdapter
    community: CommunityAdapter

    if isinstance(data, _InteractionAdapter | JumpediaAdapter):
        interaction, _ = _get_jumpedia_and_interaction(data)
        community = get_current_community(data)
    else:
        community = data
        interaction = community.jumpedia.interaction

    del data

    return community.get_or_create_community_user(
        get_or_create_specified_or_current_jumpedia_user(
            interaction, user, override_jumpedia_rank=override_jumpedia_rank
        ),
        override_community_rank=override_community_rank,
    )


@t.overload
def get_specified_or_ia_user_selected_or_default_list(
    community: CommunityAdapter,
    list: str | None,
    /,
    *,
    error: t.Literal[True] = ...,
) -> ListAdapter:
    pass


@t.overload
def get_specified_or_ia_user_selected_or_default_list(
    community: CommunityAdapter,
    list: str | None,
    /,
    *,
    error: t.Literal[False],
) -> ListAdapter | None:
    pass


@t.overload
def get_specified_or_ia_user_selected_or_default_list(
    jumpedia: JumpediaAdapter,
    list: str | None,
    /,
    *,
    error: t.Literal[True] = ...,
) -> ListAdapter:
    pass


@t.overload
def get_specified_or_ia_user_selected_or_default_list(
    jumpedia: JumpediaAdapter,
    list: str | None,
    /,
    *,
    error: t.Literal[False],
) -> ListAdapter | None:
    pass


@t.overload
def get_specified_or_ia_user_selected_or_default_list(
    interaction: _InteractionAdapter,
    list: str | None,
    /,
    *,
    error: t.Literal[True] = ...,
) -> ListAdapter:
    pass


@t.overload
def get_specified_or_ia_user_selected_or_default_list(
    interaction: _InteractionAdapter,
    list: str | None,
    /,
    *,
    error: t.Literal[False],
) -> ListAdapter | None:
    pass


def get_specified_or_ia_user_selected_or_default_list(
    data: CommunityAdapter | JumpediaAdapter | _InteractionAdapter,
    list: str | None = None,
    /,
    *,
    error: bool = True,
) -> ListAdapter | None:
    from _adapters._community import CommunityAdapter

    community: CommunityAdapter

    if isinstance(data, CommunityAdapter):
        community = data
    else:
        community = get_current_community(_get_jumpedia_and_interaction(data)[1])

    del data

    if list is not None:
        return community.get_list(list)

    community_user = get_or_create_specified_or_current_community_user(
        community, community.jumpedia.interaction.ia_jumpedia_user
    )

    selected_list = community_user.get_selected_list()

    if selected_list is not None:
        return selected_list

    return (
        community.get_default_selected_list()
        if error
        else community.get_default_selected_list(None)
    )
