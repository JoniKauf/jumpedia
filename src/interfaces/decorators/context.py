import functools
import types as ts
import typing as t
from dataclasses import dataclass

import discord
from discord.ext import commands
from sqlalchemy.orm import Session

import db.session
from domain import errors
from domain.entities.user import UserEntity
from domain.enums.rank import AnyRankT, MetaRank, ServerRank
from domain.types.id import ID
from domain.types.server import ServerID
from domain.types.user import UserID
from domain.value_objects.string import StrStore
from domain.value_objects.user import UserName
from interfaces.contexts.command import CommandContext, PublicServices
from interfaces.message import format, messages
from repositories.attribute import AttributeRepository
from repositories.community import CommunityRepository
from repositories.community_user import CommunityUserRepository
from repositories.dtos.user import UserInsert
from repositories.list import ListRepository
from repositories.server import ServerRepository
from repositories.task import TaskRepository
from repositories.user import UserRepository
from services.attribute import AttributeService
from services.community import (
    CommunityAccessService,
    CommunityQueryService,
    CommunityService,
)
from services.contexts.interacting_user import InteractingUserContext
from services.list import ListService
from services.permission import PermissionService
from services.user import UserService

if t.TYPE_CHECKING:
    from interfaces.base import BaseInterface


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
                t"You have the rank {format.mention_body(e.rank)}, but you at least need the rank {format.mention_body(e.required)} to perform this action!",
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


def _get_server_rank(member: discord.Member) -> ServerRank:
    owner = member.guild.owner

    if owner is not None and member.id == owner.id:
        return ServerRank.OWNER

    if member.guild_permissions.administrator:
        return ServerRank.ADMINISTRATOR

    return ServerRank.USER


def _create_services_object(session: Session, member: discord.Member):
    user_repo = UserRepository(session)
    server_repo = ServerRepository(session)
    community_repo = CommunityRepository(session)
    community_user_repo = CommunityUserRepository(session)
    list_repo = ListRepository(session)
    attribute_repo = AttributeRepository(session)
    task_repo = TaskRepository(session)

    user_service = UserService(user_repo)

    community_user_service = CommunityUserService(community_user_repo, user_service)

    interacting_user_ctx = InteractingUserContext(
        user_service.get_or_create(
            UserInsert(
                UserID(ID(member.id)),
                UserName(member.name),
            )
        ),
        _get_server_rank(member),
        ServerID(ID(member.guild.id)),
    )

    permission_service = PermissionService(interacting_user_ctx)
    community_access_service = CommunityAccessService(
        interacting_user_ctx, community_repo, community_user_service
    )
    community_query_service = CommunityQueryService(
        interacting_user_ctx,
        community_repo,
        community_access_service,
        community_user_repo,
        list_repo,
        task_repo,
    )
    list_service = ListService(
        interacting_user_ctx, list_repo, permission_service, community_access_service
    )
    community_service = CommunityService(
        interacting_user_ctx,
        community_repo,
        community_access_service,
        permission_service,
        community_user_service,
        list_service,
        server_repo,
    )
    attribute_service = AttributeService(
        interacting_user_ctx, attribute_repo, permission_service
    )

    return PublicServices(
        community_service, community_query_service, list_service, attribute_service
    )


type FuncIn[T, **P] = t.Callable[
    t.Concatenate[T, CommandContext, P],
    ts.CoroutineType[None, None, None],
]

type FuncOut[T, **P] = t.Callable[
    t.Concatenate[T, discord.Interaction, P], ts.CoroutineType[None, None, None]
]


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

                    services = _create_services_object(session, member)

                    await func(
                        self,
                        CommandContext(
                            services,
                            interaction,
                        ),
                        *args,
                        **kwargs,
                    )
                except errors.DomainError as e:
                    await _handle_domain_error(interaction, e)
                except (errors.InternalError, Exception):
                    await messages.error(
                        interaction,
                        t"Unhandled",
                        t"An unhandled exception (unexpected error) occurred!\n"
                        + t"Please try again later...",
                    )
                    raise

        return wrapper

    return decorator
