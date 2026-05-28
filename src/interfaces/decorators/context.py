import functools

from dataclasses import dataclass
import discord
from discord.ext import commands
import typing as t
import types as ts

from sqlalchemy.orm import Session

import db.session
from domain.entities.user import UserEntity
from domain.enums.rank import AnyRankT, MetaRank, ServerRank
from domain import errors
from domain.types.id import ID
from domain.value_objects.string import StrStore
from interfaces.contexts.command import CommandContext
from interfaces.contexts.interacting_user import InteractingUserContext
from interfaces.message import format, messages
from repositories.user import CommunityRank
from services.services import Services
from services.user import UserService

if t.TYPE_CHECKING:
    from interfaces.base import BaseInterface


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
                t"You have the rank {format.Mention(e.rank).mention}, but you at least need the rank {format.Mention(e.required).mention} to perform this action!",
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
                            Services(
                                UserService(
                                    session,
                                    this_services_object
                                )
                            ),
                            interaction,
                            InteractingUserContext(
                                self.user_service._get_or_create(
                                    UserEntity(
                                        ID(member.id),
                                        StrStore(member.name),
                                    )
                                ),
                                self.get_server_rank(member),
                                member.guild.id,
                            ),
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
