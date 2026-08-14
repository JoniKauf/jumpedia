import functools
import types as ts
import typing as t

import discord
from sqlalchemy.orm import Session

import jumpedia.db.session
from jumpedia.domain.enums.rank import ServerRank
from jumpedia.domain.errors.business import (
    AnyBusinessErrorT,
    BusinessError,
    NotInServer,
)
from jumpedia.domain.errors.internal import InternalError
from jumpedia.domain.typing.common import ID
from jumpedia.domain.typing.server import ServerID
from jumpedia.domain.typing.user import UserID
from jumpedia.domain.value_objects.user import UserNameStr
from jumpedia.interfaces.base import BaseInterface
from jumpedia.interfaces.contexts.command import CommandContext, PublicServices
from jumpedia.interfaces.decorators.with_context import (
    _domain_error_handling,
    _dsl_error_handling,
)
from jumpedia.interfaces.dsls.core.errors.base import AnyDslErrorT, DslError
from jumpedia.interfaces.dsls.core.errors.eval import AnyEvalErrorT
from jumpedia.interfaces.dsls.core.errors.lex import AnyLexErrorT
from jumpedia.interfaces.dsls.core.errors.parse import AnyParseErrorT
from jumpedia.interfaces.message import messages
from jumpedia.interfaces.message.formatting import F
from jumpedia.repositories.attribute import AttributeRepository
from jumpedia.repositories.collection_entry import CollectionEntryRepository
from jumpedia.repositories.community import CommunityRepository
from jumpedia.repositories.dtos.user import UserInsert
from jumpedia.repositories.field_slot import FieldSlotRepository
from jumpedia.repositories.list import ListRepository
from jumpedia.repositories.member import MemberRepository
from jumpedia.repositories.member_field_slot import MemberFieldSlotRepository
from jumpedia.repositories.member_task import MemberTaskRepository
from jumpedia.repositories.server import ServerRepository
from jumpedia.repositories.task import TaskRepository
from jumpedia.repositories.user import UserRepository
from jumpedia.services.attribute import (
    AttributeAccessService,
    AttributePrepareService,
    AttributeQueryService,
    AttributeService,
)
from jumpedia.services.community import (
    CommunityAccessService,
    CommunityPrepareService,
    CommunityQueryService,
    CommunityService,
)
from jumpedia.services.contexts.interacting_user import InteractingUserContext
from jumpedia.services.internal.collection import CollectionBuildService
from jumpedia.services.internal.edit_mode import EditModeService
from jumpedia.services.internal.field_mapping import (
    FieldMappingBuildService,
    FieldMappingExtractionService,
    FieldMappingService,
    FieldMappingTransformationService,
)
from jumpedia.services.internal.permission import PermissionService
from jumpedia.services.internal.slot_type import SlotTypeService
from jumpedia.services.internal.strs import StrsService
from jumpedia.services.list import (
    ListAccessService,
    ListPrepareService,
    ListQueryService,
    ListService,
)
from jumpedia.services.member import (
    MemberAccessService,
    MemberExistenceService,
    MemberQueryService,
    MemberService,
)
from jumpedia.services.member_task import (
    MemberTaskAccessService,
    MemberTaskQueryService,
    MemberTaskService,
)
from jumpedia.services.server import ServerService
from jumpedia.services.task import (
    TaskAccessService,
    TaskPrepareService,
    TaskQueryService,
    TaskService,
)
from jumpedia.services.user import UserAccessService, UserExistenceService, UserService


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

    ctx = InteractingUserContext(
        user_existence_service.get_or_create(
            UserInsert(UserID(ID(member.id)), UserNameStr(member.name))
        ),
        _get_server_rank(member),
        ServerID(ID(member.guild.id)),
    )
    user_access_service = UserAccessService(ctx, user_existence_service)

    community_access_service = CommunityAccessService(ctx, community_repository)

    member_existence_service = MemberExistenceService(
        member_repository, user_existence_service
    )
    permission_service = PermissionService(ctx)
    member_access_service = MemberAccessService(
        ctx,
        member_repository,
        community_access_service,
        member_existence_service,
        permission_service,
        user_access_service,
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
        member_task_repository, member_access_service, task_access_service
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
        member_access_service,
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
        task_repository,
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
        user_existence_service,
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
        list_access_service,
        member_access_service,
        member_existence_service,
        permission_service,
        user_existence_service,
    )
    member_query_service = MemberQueryService(
        ctx,
        community_repository,
        list_repository,
        member_existence_service,
        user_access_service,
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
        member_query=member_query_service,
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
            try:
                await interaction.response.defer()
            except discord.NotFound:
                # Sometimes happens when there is some kind of big lag.
                # Ignore this request and just let the user redo it as we are too late
                # to save anything either way.
                return

            with jumpedia.db.session.get_session() as session:
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
                except t.get_args(AnyBusinessErrorT.__value__) as e:
                    e = t.cast(AnyBusinessErrorT, e)
                    await _domain_error_handling.handle_domain_error(interaction, e)

                except DslError as e:
                    if isinstance(e, t.get_args(AnyLexErrorT.__value__)):
                        e = t.cast(AnyLexErrorT, e)
                        await _dsl_error_handling.handle_lex_error(interaction, e)

                    elif isinstance(e, t.get_args(AnyParseErrorT.__value__)):
                        e = t.cast(AnyParseErrorT, e)
                        await _dsl_error_handling.handle_parse_error(interaction, e)

                    elif isinstance(e, t.get_args(AnyEvalErrorT.__value__)):
                        e = t.cast(AnyEvalErrorT, e)
                        await _dsl_error_handling.handle_eval_error(interaction, e)

                    else:
                        raise AssertionError(
                            f"'{e=}' is not any of the 3 DSL error types"
                        )

                except InternalError, Exception:
                    await messages.error(
                        interaction,
                        t"Unhandled",
                        t"An unhandled exception (unexpected error) occurred!\n"
                        + t"Please try again later...",
                    )
                    raise

        return wrapper

    return decorator
