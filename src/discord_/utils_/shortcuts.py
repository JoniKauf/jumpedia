import typing as t

import discord as dc

from adapters import errors
from adapters._community import CommunityAdapter
from adapters._jumpedia import JumpediaAdapter
from adapters._list import ListAdapter
from adapters._user import CommunityUserAdapter, JumpediaUserAdapter, UserAdapter
from adapters.interaction import InteractionAdapter
from utils.rank import CommunityRank, JumpediaRank


def _get_jumpedia_and_interaction(
    data: JumpediaAdapter | InteractionAdapter, /
) -> tuple[InteractionAdapter, JumpediaAdapter]:
    if isinstance(data, InteractionAdapter):
        return data, data.jumpedia

    return data.interaction, data


@t.overload
def get_current_community(jumpedia: JumpediaAdapter, /) -> CommunityAdapter:
    pass


@t.overload
def get_current_community(interaction: InteractionAdapter, /) -> CommunityAdapter:
    pass


def get_current_community(
    data: JumpediaAdapter | InteractionAdapter, /
) -> CommunityAdapter:
    interaction, jumpedia = _get_jumpedia_and_interaction(data)

    del data

    community_s = jumpedia._o.get_community_by_server_id(
        interaction._c, interaction.current_server.id
    )

    if community_s is None:
        raise errors.ServerNotConnectedToACommunity()

    return CommunityAdapter(community_s, jumpedia)


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
    interaction: InteractionAdapter,
    user: None | dc.User,
    /,
    *,
    override_jumpedia_rank: JumpediaRank | None = None,
) -> JumpediaUserAdapter:
    pass


def get_or_create_specified_or_current_jumpedia_user(
    data: JumpediaAdapter | InteractionAdapter,
    user: None | dc.User,
    /,
    *,
    override_jumpedia_rank: JumpediaRank | None = None,
) -> JumpediaUserAdapter:
    jumpedia: JumpediaAdapter = (
        data if isinstance(data, JumpediaAdapter) else data.jumpedia
    )

    del data

    return jumpedia.get_or_create_jumpedia_user(
        (
            jumpedia.interaction.current_user
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
    interaction: InteractionAdapter,
    user: dc.User | None,
    /,
    *,
    override_jumpedia_rank: JumpediaRank | None = None,
    override_community_rank: CommunityRank | None = None,
) -> CommunityUserAdapter:
    pass


def get_or_create_specified_or_current_community_user(
    data: CommunityAdapter | JumpediaAdapter | InteractionAdapter,
    user: dc.User | JumpediaUserAdapter | None,
    /,
    *,
    override_jumpedia_rank: JumpediaRank | None = None,
    override_community_rank: CommunityRank | None = None,
) -> CommunityUserAdapter:
    if isinstance(user, JumpediaUserAdapter):
        assert isinstance(data, CommunityAdapter)

        return data.get_or_create_community_user(
            user, override_community_rank=override_community_rank
        )

    interaction: InteractionAdapter
    community: CommunityAdapter

    if isinstance(data, InteractionAdapter | JumpediaAdapter):
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
def get_specified_or_selected_or_default_list(
    user: CommunityUserAdapter,
    list: str | None,
    /,
    *,
    error: t.Literal[True] = ...,
) -> ListAdapter:
    pass


@t.overload
def get_specified_or_selected_or_default_list(
    user: CommunityUserAdapter,
    list: str | None,
    /,
    *,
    error: t.Literal[False],
) -> ListAdapter | None:
    pass


@t.overload
def get_specified_or_selected_or_default_list(
    community: CommunityAdapter,
    user: dc.User | None,
    list: str | None,
    /,
    *,
    error: t.Literal[True] = ...,
) -> ListAdapter:
    pass


@t.overload
def get_specified_or_selected_or_default_list(
    community: CommunityAdapter,
    user: dc.User | None,
    list: str | None,
    /,
    *,
    error: t.Literal[False],
) -> ListAdapter | None:
    pass


@t.overload
def get_specified_or_selected_or_default_list(
    jumpedia: JumpediaAdapter,
    user: dc.User | None,
    list: str | None,
    /,
    *,
    error: t.Literal[True] = ...,
) -> ListAdapter:
    pass


@t.overload
def get_specified_or_selected_or_default_list(
    jumpedia: JumpediaAdapter,
    user: dc.User | None,
    list: str | None,
    /,
    *,
    error: t.Literal[False],
) -> ListAdapter | None:
    pass


@t.overload
def get_specified_or_selected_or_default_list(
    interaction: InteractionAdapter,
    user: dc.User | None,
    list: str | None,
    /,
    *,
    error: t.Literal[True] = ...,
) -> ListAdapter:
    pass


@t.overload
def get_specified_or_selected_or_default_list(
    interaction: InteractionAdapter,
    user: dc.User | None,
    list: str | None,
    /,
    *,
    error: t.Literal[False],
) -> ListAdapter | None:
    pass


def get_specified_or_selected_or_default_list(
    data: (
        CommunityUserAdapter | CommunityAdapter | JumpediaAdapter | InteractionAdapter
    ),
    user_or_list: str | dc.User | None,
    optional_list: str | None = None,
    /,
    *,
    error: bool = True,
) -> ListAdapter | None:
    community_user: CommunityUserAdapter
    list: str | None

    if isinstance(data, CommunityUserAdapter):
        assert user_or_list is None or isinstance(user_or_list, str)

        community_user = data
        list = user_or_list

    else:
        assert user_or_list is None or isinstance(user_or_list, dc.User)
        assert optional_list is None or isinstance(optional_list, str)

        list = optional_list
        community_user = get_or_create_specified_or_current_community_user(
            data, user_or_list
        )

    del data

    community = community_user.community

    if list is not None:
        return community.get_list(list)

    list_obj = community_user.get_selected_list()

    if list_obj is not None:
        return list_obj

    return (
        community.get_default_selected_list()
        if error
        else community.get_default_selected_list(None)
    )
