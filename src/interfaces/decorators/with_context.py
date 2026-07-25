import functools
import types as ts
import typing as t

import discord
from sqlalchemy.orm import Session

from domain.entities.user import UserEntity
from domain.enums.rank import ServerRank
from domain.errors.business import BusinessError, NotInServer
from domain.errors.internal import InternalError
from domain.typing.common import ID
from domain.typing.server import ServerID
from domain.typing.user import UserID
from domain.value_objects.user import UserNameStr
from interfaces.base import BaseInterface
from interfaces.contexts.command import CommandContext, PublicServices
from interfaces.dsls.core.errors.base import DslError
from interfaces.message import messages
from interfaces.message.formatting import F
from repositories.attribute import AttributeRepository
from repositories.collection_entry import CollectionEntryRepository
from repositories.community import CommunityRepository
from repositories.dtos.user import UserInsert
from repositories.field_slot import FieldSlotRepository
from repositories.list import ListRepository
from repositories.member import MemberRepository
from repositories.member_field_slot import MemberFieldSlotRepository
from repositories.member_task import MemberTaskRepository
from repositories.server import ServerRepository
from repositories.task import TaskRepository
from repositories.user import UserRepository
from services.attribute import (
    AttributeAccessService,
    AttributePrepareService,
    AttributeQueryService,
    AttributeService,
)
from services.community import (
    CommunityAccessService,
    CommunityPrepareService,
    CommunityQueryService,
    CommunityService,
)
from services.contexts.interacting_user import InteractingUserContext
from services.internal.collection import CollectionBuildService
from services.internal.edit_mode import EditModeService
from services.internal.field_mapping import (
    FieldMappingBuildService,
    FieldMappingExtractionService,
    FieldMappingService,
    FieldMappingTransformationService,
)
from services.internal.permission import PermissionService
from services.internal.slot_type import SlotTypeService
from services.internal.strs import StrsService
from services.list import (
    ListAccessService,
    ListPrepareService,
    ListQueryService,
    ListService,
)
from services.member import MemberAccessService, MemberExistenceService, MemberService
from services.member_task import (
    MemberTaskAccessService,
    MemberTaskQueryService,
    MemberTaskService,
)
from services.server import ServerService
from services.task import (
    TaskAccessService,
    TaskPrepareService,
    TaskQueryService,
    TaskService,
)
from services.user import UserExistenceService, UserService
import db.session


async def _handle_domain_error(
    interaction: discord.Interaction, e: BusinessError
) -> None:
    match e:
        case NotInServer():
            await messages.error(
                interaction,
                t"Not In A Server",
                t"The specified command needs to be executed in a server!",
            )

        case NotInCommunity():
            await messages.error(
                interaction,
                t"Not In A Community",
                t"The specified command needs to be executed in a community!",
            )

        case NotAllowed():
            await messages.error(
                interaction,
                t"Not Allowed",
                t"You have the {F.mention(e.rank)}, but you at least need the {F.mention(e.required)} to perform this action!",
            )

        case EmptyString():
            await messages.error(
                interaction,
                t"Empty String",
                t'You entered an empty or whitespace-only string (`""`), which is not allowed!',
            )

        case DoubleBacktick():
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


def _create_public_services_object(
    session: Session, member: discord.Member
) -> PublicServices:
    attribute_repository = AttributeRepository(session)
    collection_entry_repository = CollectionEntryRepository(session)
    community_repository = CommunityRepository(session)
    field_slot_repository = FieldSlotRepository(session)
    list_repository = ListRepository(session)
    member_repository = MemberRepository(session)
    member_field_slot_repository = MemberFieldSlotRepository(session)
    member_task_repository = MemberTaskRepository(session)
    task_repository = TaskRepository(session)
    user_repository = UserRepository(session)
    server_repository = ServerRepository(session)

    user_existence_service = UserExistenceService(user_repository)
    user_entity = user_existence_service.get_or_create(UserInsert(UserID(ID(member.id)), UserNameStr(member.name)))
    ctx = InteractingUserContext(user_entity, _get_server_rank(member), ServerID(ID(member.guild.id)))

    community_access_service = CommunityAccessService(ctx, community_repository)

    member_existence_service = MemberExistenceService(
        ctx,
        member_repository, user_existence_service
    )
    permission_service = PermissionService(ctx)
    member_access_service = MemberAccessService(
        ctx,
        member_repository,
        community_access_service,
        member_existence_service,
        permission_service,
        user_existence_service,
    )
    list_access_service = ListAccessService(list_repository, member_access_service)
    attribute_access_service = AttributeAccessService(
        ctx, attribute_repository, list_access_service
    )
    slot_type_service = SlotTypeService()
    strs_service = StrsService()
    collection_build_service = CollectionBuildService(slot_type_service, strs_service)
    edit_mode_service = EditModeService(strs_service)
    field_mapping_extraction_service = FieldMappingExtractionService()
    field_mapping_transformation_service = FieldMappingTransformationService(
        slot_type_service
    )
    task_access_service = TaskAccessService(task_repository, list_access_service)
    member_task_access_service = MemberTaskAccessService(
        member_existence_service, member_task_repository, task_access_service
    )
    field_mapping_service = FieldMappingService(
        attribute_repository,
        collection_entry_repository,
        field_slot_repository,
        member_field_slot_repository,
        member_repository,
        member_task_repository,
        task_repository,
        list_access_service,
        field_mapping_extraction_service,
        field_mapping_transformation_service,
        member_existence_service,
        member_task_access_service,
        slot_type_service,
        task_access_service,
    )
    field_mapping_build_service = FieldMappingBuildService(
        edit_mode_service, slot_type_service
    )

    attribute_prepare_service = AttributePrepareService(
        attribute_access_service, permission_service
    )
    attribute_service = AttributeService(
        attribute_repository,
        collection_entry_repository,
        field_slot_repository,
        attribute_access_service,
        collection_build_service,
        edit_mode_service,
        list_access_service,
        permission_service,
        strs_service,
    )
    attribute_query_service = AttributeQueryService(
        attribute_repository,
        collection_entry_repository,
        attribute_access_service,
        list_access_service,
        member_access_service,
    )
    list_service = ListService(
        attribute_repository,
        list_repository,
        list_access_service,
        member_access_service,
        permission_service,
    )
    community_prepare_service = CommunityPrepareService(
        member_access_service, permission_service
    )
    community_service = CommunityService(
        ctx,
        community_repository,
        server_repository,
        list_access_service,
        list_service,
        member_access_service,
        member_existence_service,
        permission_service,
    )
    community_query_service = CommunityQueryService(
        community_repository,
        list_repository,
        member_repository,
        task_repository,
        community_access_service,
    )
    list_prepare_service = ListPrepareService(list_access_service, permission_service)
    list_query_service = ListQueryService(
        attribute_repository,
        list_repository,
        task_repository,
        community_access_service,
        list_access_service,
    )
    member_service = MemberService(
        member_repository,
        member_access_service,
        member_existence_service,
        permission_service,
        user_existence_service,
    )
    member_task_service = MemberTaskService(
        attribute_repository,
        collection_entry_repository,
        member_field_slot_repository,
        member_task_repository,
        field_mapping_build_service,
        member_access_service,
        task_access_service,
    )
    member_task_query_service = MemberTaskQueryService(field_mapping_service)
    server_service = ServerService(
        ctx,
        community_repository,
        server_repository,
        community_access_service,
        permission_service,
    )
    task_prepare_service = TaskPrepareService(permission_service, task_access_service)
    task_service = TaskService(
        attribute_repository,
        collection_entry_repository,
        field_slot_repository,
        task_repository,
        edit_mode_service,
        field_mapping_build_service,
        list_access_service,
        permission_service,
        strs_service,
        task_access_service,
    )
    task_query_service = TaskQueryService(field_mapping_service)
    user_service = UserService(
        user_repository, permission_service, user_existence_service
    )

    return PublicServices(
        attribute=attribute_service,
        attribute_prepare=attribute_prepare_service,
        attribute_query=attribute_query_service,
        community=community_service,
        community_prepare=community_prepare_service,
        community_query=community_query_service,
        list=list_service,
        list_prepare=list_prepare_service,
        list_query=list_query_service,
        member=member_service,
        member_task=member_task_service,
        member_task_query=member_task_query_service,
        server=server_service,
        task=task_service,
        task_prepare=task_prepare_service,
        task_query=task_query_service,
        user=user_service,
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
                        raise NotInServer()

                    services = _create_public_services_object(session, member)

                    await func(
                        self,
                        CommandContext(
                            services,
                            interaction,
                        ),
                        *args,
                        **kwargs,
                    )
                except BusinessError as e:
                    await _handle_domain_error(interaction, e)
                except DslError as e:
                    ...
                except InternalError:
                    await messages.error(
                        interaction,
                        t"Unhandled",
                        t"An unhandled exception (unexpected error) occurred!\n"
                        + t"Please try again later...",
                    )
                    raise

        return wrapper

    return decorator
