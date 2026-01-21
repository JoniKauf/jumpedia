import typing as t

import discord as dc

from dc_utils import errors
from dc_utils.rank import CommunityRank, JumpediaRank

if t.TYPE_CHECKING:
    from adapting._community import CommunityAdapter
    from adapting._jumpedia import JumpediaAdapter
    from adapting._list import ListAdapter
    from adapting._user import CommunityUserAdapter, JumpediaUserAdapter, UserAdapter
    from adapting.interaction import InteractionAdapter


def _get_jumpedia_and_interaction(
    data: JumpediaAdapter | InteractionAdapter, /
) -> tuple[InteractionAdapter, JumpediaAdapter]:
    from adapting.interaction import InteractionAdapter

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
    from adapting._community import CommunityAdapter

    interaction, jumpedia = _get_jumpedia_and_interaction(data)

    del data

    tup = jumpedia._o.get_community_by_server_id(interaction._c, interaction.server.id)

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
    from adapting._jumpedia import JumpediaAdapter
    from adapting._user import UserAdapter

    jumpedia: JumpediaAdapter = (
        data if isinstance(data, JumpediaAdapter) else data.jumpedia
    )

    del data

    return jumpedia.get_or_create_jumpedia_user(
        (
            jumpedia.interaction.user
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
    from adapting._community import CommunityAdapter
    from adapting._jumpedia import JumpediaAdapter
    from adapting._user import JumpediaUserAdapter
    from adapting.interaction import InteractionAdapter

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
    from adapting._community import CommunityUserAdapter

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
