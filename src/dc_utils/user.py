import re
import typing as t

import discord as dc

from domain.enum.rank import AnyRankT, CommunityRank, JumpediaRank, ServerRank

from . import errors, shortcuts

if t.TYPE_CHECKING:
    from _adapters._jumpedia import JumpediaAdapter
    from _adapters._user import JumpediaUserAdapter

MAX_NAME_LENGTH: t.Final[int] = 32

MIN_ID: t.Final[int] = 0
MAX_ID: t.Final[int] = 2**64 - 1  # Snowflake is Unsigned Long int

MENTION_PATTERN = re.compile(r"^<@([0-9]{0,20})>$")


def _int_to_id(i: int) -> int:
    if not (MIN_ID <= i <= MAX_ID):
        raise ValueError("Out of range")

    return i


def _str_to_id(s: str) -> int:
    try:
        identifier = int(s)
    except ValueError:
        pass
    else:
        return _int_to_id(identifier)

    s = s.strip()

    match = MENTION_PATTERN.match(s)

    if not match:
        raise ValueError

    return int(match.group(1))


def identifier_to_id(identifier: str | int) -> int:
    if isinstance(identifier, int):
        return _int_to_id(identifier)

    return _str_to_id(identifier)


def validate_allowed(
    interaction: dc.Interaction, rank_required: AnyRankT, *ranks_required: AnyRankT
) -> None:
    from dc_utils import command

    server_rank: ServerRank | None = None
    jumpedia_rank: JumpediaRank | None = None
    community_rank: CommunityRank | None = None

    jumpedia_and_user: tuple[JumpediaAdapter, JumpediaUserAdapter] | None = None

    with command.InteractionAdapterContext(interaction) as ia:

        def get_jumpedia_and_jumpedia_user() -> (
            tuple[JumpediaAdapter, JumpediaUserAdapter]
        ):
            nonlocal jumpedia_and_user

            if jumpedia_and_user is not None:
                return jumpedia_and_user

            jumpedia_user = shortcuts.get_or_create_specified_or_current_jumpedia_user(
                ia.jumpedia, None
            )

            jumpedia_and_user = (ia.jumpedia, jumpedia_user)

            return jumpedia_and_user

        def get_jumpedia_rank() -> JumpediaRank:
            nonlocal jumpedia_rank

            if jumpedia_rank is not None:
                return jumpedia_rank

            jumpedia_rank = get_jumpedia_and_jumpedia_user()[1].jumpedia_rank

            return jumpedia_rank

        def get_server_rank() -> ServerRank:
            nonlocal server_rank

            if server_rank is not None:
                return server_rank

            server_rank = ia.ia_server_member.server_rank

            return server_rank

        def get_community_rank() -> CommunityRank:
            nonlocal community_rank

            if community_rank is not None:
                return community_rank

            jumpedia, jumpedia_user = get_jumpedia_and_jumpedia_user()

            community_rank = (
                shortcuts.get_or_create_specified_or_current_community_user(
                    shortcuts.get_current_community(jumpedia), jumpedia_user
                ).community_rank
            )

            return community_rank

        for req in (rank_required, *ranks_required):
            # Power == 0 required
            if not req:
                continue

            # Doesn't need database, therefore cheapest, therefore do first
            if isinstance(req, ServerRank):
                sr = get_server_rank()

                if sr >= req:
                    continue

                if get_jumpedia_rank():
                    continue

                raise errors.NotPermittedError(sr, req)

            if isinstance(req, JumpediaRank):
                jr = get_jumpedia_rank()

                if jr >= req:
                    continue

                raise errors.NotPermittedError(jr, req)

            if isinstance(req, CommunityRank):
                if get_jumpedia_rank():
                    continue

                cr = get_community_rank()

                if cr >= req:
                    continue

                raise errors.NotPermittedError(cr, req)

            t.assert_never(req)


def validate_allowed_for_others(
    interaction: dc.Interaction, user: dc.User | None, rank_required: AnyRankT
) -> None:
    if user is None or interaction.user.id == user.id:
        return

    try:
        return validate_allowed(interaction, rank_required)
    except errors.NotPermittedError as e:
        raise errors.NotEnoughPowerToAffectOtherUsers(e.my_rank, e.rank_required)
