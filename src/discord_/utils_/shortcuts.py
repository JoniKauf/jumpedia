import typing as t

import discord as dc

from adapters import errors
from adapters._community import CommunityAdapter
from adapters._list import ListAdapter
from adapters._jumpedia import JumpediaAdapter
from adapters._user import CommunityUserAdapter, JumpediaUserAdapter, UserAdapter
from adapters.interaction import InteractionAdapter
from utils.rank import CommunityRank, JumpediaRank


def get_current_community(data: InteractionAdapter) -> CommunityAdapter:
    ia: InteractionAdapter = data
    jumpedia: JumpediaAdapter = data.jumpedia

    del data

    community_s = jumpedia._s.get_community_by_server_id(ia.current_server.id)

    if community_s is None:
        raise errors.ServerNotConnectedToACommunityFeedbackError()

    return CommunityAdapter(community_s, jumpedia)


def get_or_create_specified_or_current_jumpedia_user(
    data: JumpediaAdapter | InteractionAdapter,
    user: None | dc.User,
    *,
    override_jumpedia_rank: JumpediaRank | None = None,
) -> JumpediaUserAdapter:
    jumpedia: JumpediaAdapter = data if isinstance(data, JumpediaAdapter) else data.jumpedia
    
    del data

    return jumpedia.get_or_create_jumpedia_user(
        jumpedia.interaction.current_user if user is None else UserAdapter(user, jumpedia.interaction),
        override_jumpedia_rank=override_jumpedia_rank,
    )


def get_or_create_specified_or_current_community_user(
    data: CommunityAdapter | InteractionAdapter,
    user: dc.User | None,
    *,
    override_jumpedia_rank: JumpediaRank | None = None,
    override_community_rank: CommunityRank | None = None,
) -> CommunityUserAdapter:
    community: CommunityAdapter
    ia: InteractionAdapter

    if isinstance(data, InteractionAdapter):
        community = get_current_community(data)
        ia = data
    else:
        community = data
        ia = community.jumpedia.interaction

    del data

    return community.get_or_create_community_user(
        get_or_create_specified_or_current_jumpedia_user(
            ia, user, override_jumpedia_rank=override_jumpedia_rank
        ),
        override_community_rank=override_community_rank,
    )


@t.overload
def get_specified_or_selected_or_default_list(
    data: CommunityUserAdapter | tuple[CommunityAdapter | InteractionAdapter, dc.User | None],
    list: str | None,
    *,
    error: t.Literal[True] = ...,
) -> ListAdapter:
    pass


@t.overload
def get_specified_or_selected_or_default_list(
    data: CommunityUserAdapter | tuple[CommunityAdapter | InteractionAdapter, dc.User | None],
    list: str | None,
    *,
    error: t.Literal[False],
) -> ListAdapter | None:
    pass


def get_specified_or_selected_or_default_list(
    data: CommunityUserAdapter | tuple[CommunityAdapter | InteractionAdapter, dc.User | None],
    list: str | None,
    *,
    error: bool = True,
) -> ListAdapter | None:
    community_user: CommunityUserAdapter

    if isinstance(data, tuple):
        community_user = get_or_create_specified_or_current_community_user(*data)
    else:
        community_user = data

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
