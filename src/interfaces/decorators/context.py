import functools

from dataclasses import dataclass
import discord
from discord.ext import commands
import typing as t
import types as ts

from sqlalchemy.orm import Session

import db.session
from domain.entities.user import UserEntity
from domain.enums.rank import AnyRankT, JumpediaRank, ServerRank
from domain import errors
from domain.value_objects.strings import StrStore
from interfaces.message import formatting, messages
from repositories.user import CommunityRank

if t.TYPE_CHECKING:
    from interfaces.base import BaseInterface


@dataclass(frozen=True)
class CommandContext:
    session: Session
    user: UserEntity
    server_rank: ServerRank


def _get_server_rank(member: discord.Member) -> ServerRank:
    owner = member.guild.owner

    if owner is not None and member.id == owner.id:
        return ServerRank.OWNER

    if member.guild_permissions.administrator:
        return ServerRank.ADMINISTRATOR

    return ServerRank.USER


def _validate_rank(
    rank_required: AnyRankT,
    member: discord.Member,
    interface: BaseInterface,
) -> None:
    if not rank_required:
        return

    jumpedia_user = interface.user_service.get_or_create_user(
        member.id, StrStore(member.global_name or member.name)
    )
    jumpedia_rank = JumpediaRank(jumpedia_user.power)

    if isinstance(rank_required, JumpediaRank):
        if rank_required <= jumpedia_rank:
            return

        raise errors.NotAllowed(jumpedia_rank, rank_required)

    if jumpedia_rank.value > 0:
        return

    if isinstance(rank_required, ServerRank):
        server_rank = _get_server_rank(member)

        if rank_required <= server_rank:
            return

        raise errors.NotAllowed(server_rank, rank_required)

    assert isinstance(rank_required, CommunityRank)

    community = interface.community_service.get_by_server_id(member.guild.id)

    if community is None:
        raise errors.NotInCommunity()

    community_user = interface.user_service.get_or_create_community_user(
        member.id, community.community_id
    )
    community_rank = CommunityRank(community_user.power)

    if rank_required <= community_rank:
        return

    raise errors.NotAllowed(community_rank, rank_required)


type FuncIn[T, **P] = t.Callable[
    t.Concatenate[T, CommandContext, P],
    ts.CoroutineType[None, None, None],
]

type FuncOut[T, **P] = t.Callable[
    t.Concatenate[T, discord.Interaction, P], ts.CoroutineType[None, None, None]
]


async def _handle_domain_error(
    interaction: discord.Interaction, e: errors.DomainError
) -> None:
    match e:
        case errors.NotInServer():
            await messages.error(
                interaction,
                t"Not In A Server",
                t"The specified command needs to be executed in a server!",
            )

        case errors.NotInCommunity():
            await messages.error(
                interaction,
                t"Not In A Community",
                t"The specified command needs to be executed in a community!",
            )

        case errors.NotAllowed():
            await messages.error(
                interaction,
                t"Not Allowed",
                t"You have the rank {formatting.mention(e.rank)}, but you at least need the rank {formatting.mention(e.required)} to perform this action!",
            )

        case errors.EmptyString():
            await messages.error(
                interaction,
                t"Empty String",
                t'You entered an empty or whitespace-only string (`""`), which is not allowed!',
            )

        case errors.DoubleBacktick():
            await messages.error(
                interaction,
                t"Double Backtick",
                t"You entered a string that contains a double backtick (`` ` `` `` ` ``), which is not allowed!\n"
                + t"The reason it is not allowed is because otherwise it would be impossible to correctly format Discord messages.",
            )

        case _:
            raise TypeError()


def with_context[T: BaseInterface, **P]() -> t.Callable[
    [FuncIn[T, P]],
    FuncOut[T, P],
]:
    """Adapt the discord.py command callback to fit our needs."""

    def decorator(
        func: FuncIn[T, P],
    ) -> FuncOut[T, P]:
        @functools.wraps(func)
        async def wrapper(
            self: T,
            interaction: discord.Interaction,
            *args: P.args,
            **kwargs: P.kwargs,
        ) -> None:
            await interaction.response.defer()

            with db.session.get_session() as session:
                try:
                    member = interaction.user

                    if not isinstance(member, discord.Member):
                        raise errors.NotInServer()

                    await func(
                        self,
                        CommandContext(
                            session,
                            self.user_service.get_or_create_user(
                                member.id, StrStore(member.global_name or member.name)
                            ),
                            _get_server_rank(interaction.user),
                        ),
                        *args,
                        **kwargs,
                    )
                except errors.DomainError as e:
                    await _handle_domain_error(interaction, e)
                except Exception:
                    await messages.error(
                        interaction,
                        t"Unhandled",
                        t"An unhandled exception (unexpected error) occurred!\n"
                        + t"Please try again later...",
                    )
                    raise

        return wrapper

    return decorator
