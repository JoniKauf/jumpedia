import itertools
import re
import typing as t
from dataclasses import dataclass

import discord
from discord import app_commands

from jumpedia.domain.entities.task import TaskEntity
from jumpedia.domain.enums.concept import Concept
from jumpedia.domain.enums.edit_mode import AliasEditMode, FieldMappingEditMode
from jumpedia.domain.errors.business import (
    BusinessError,
    CommandOptionMentionedMoreThanOnce,
    CommandOptionNotMentioned,
    NoCommandsInFile,
    NotABulkCommand,
    TextBeforeFirstCommandOption,
    UnknownCommandOptionChoice,
)
from jumpedia.domain.errors.internal import ProgrammingError
from jumpedia.domain.sentinels.default import DEFAULT
from jumpedia.domain.typing.common import ID
from jumpedia.domain.typing.user import UserID
from jumpedia.domain.value_objects.field_slot import FieldSlotStr
from jumpedia.domain.value_objects.list import ListNameStr
from jumpedia.domain.value_objects.user import UserNameStr
from jumpedia.interfaces import bindings
from jumpedia.interfaces.base import BaseInterface
from jumpedia.interfaces.bindings import user_ref
from jumpedia.interfaces.command import cogs, groups
from jumpedia.interfaces.contexts.command import CommandContext
from jumpedia.interfaces.decorators.with_context import with_context
from jumpedia.interfaces.dsls.core.errors.base import DslError
from jumpedia.interfaces.enums.edit_mode import (
    AliasEditModeInterfaceEnum,
    FieldMappingEditModeInterfaceEnum,
)
from jumpedia.interfaces.message import formatting, messages
from jumpedia.interfaces.message.formatting import F

# Commands that ask for a confirmation or only show data are left out.
_BULK_COMMANDS: t.Final[tuple[str, ...]] = (
    "task create",
    "task edit name",
    "task edit aliases",
    "task edit field_mapping",
    "task give",
    "task take",
    "task edit given",
)


@dataclass(frozen=True, slots=True)
class _BulkCommand:
    name: str
    options: frozendict[str, str]
    user: discord.User | None


def _execute_bulk_command(ctx: CommandContext, command: _BulkCommand) -> None:
    options = command.options
    list_name = options.get("list_name")

    match command.name:
        case "task create":
            ctx.services.task.create(
                FieldSlotStr(options["task_name"]),
                ListNameStr(options["list_name"]),
                bindings.sequence.task_aliases(options["aliases_dsl_sequence"]),
                bindings.mapping.field_mapping(options["field_mapping_dsl"]),
            )

        case "task edit name":
            ctx.services.task.edit_name(
                FieldSlotStr(options["task_name"]),
                FieldSlotStr(options["new_task_name"]),
                ListNameStr(options["list_name"]),
            )

        case "task edit aliases":
            ctx.services.task.edit_aliases(
                bindings.sequence.task_aliases(
                    options["new_task_aliases_dsl_sequence"]
                ),
                AliasEditMode(AliasEditModeInterfaceEnum[options["edit_mode"]].value),
                FieldSlotStr(options["task_name"]),
                ListNameStr(options["list_name"]),
            )

        case "task edit field_mapping":
            ctx.services.task.edit_field_mapping(
                bindings.mapping.field_mapping(options["new_field_mapping_dsl"]),
                FieldMappingEditMode(
                    FieldMappingEditModeInterfaceEnum[options["edit_mode"]].value
                ),
                FieldSlotStr(options["task_name"]),
                ListNameStr(options["list_name"]),
            )

        case "task give":
            ctx.services.member_task.give_to_user(
                FieldSlotStr(options["task_name_or_alias"]),
                DEFAULT if list_name is None else ListNameStr(list_name),
                bindings.mapping.field_mapping(options.get("user_field_mapping_dsl")),
                user_ref.user_ref(command.user),
            )

        case "task take":
            ctx.services.member_task.take_from_user(
                FieldSlotStr(options["task_name_or_alias"]),
                DEFAULT if list_name is None else ListNameStr(list_name),
                user_ref.user_ref(command.user),
            )

        case "task edit given":
            ctx.services.member_task.edit_member_field_mapping(
                bindings.mapping.field_mapping(options["new_user_field_mapping"]),
                FieldMappingEditMode(
                    FieldMappingEditModeInterfaceEnum[options["edit_mode"]].value
                ),
                user_ref.user_ref(command.user),
                FieldSlotStr(options["task_name_or_alias"]),
                DEFAULT if list_name is None else ListNameStr(list_name),
            )

        case _:
            raise ProgrammingError(
                f"'{command.name}' is a bulk command but not executed"
            )


class TaskInterface(
    BaseInterface, group_name=cogs.cog_concept_to_group_name(Concept.TASK, plural=False)
):
    edit_group = groups.create_edit_group()

    @app_commands.command()
    @with_context()
    async def info(
        self, ctx: CommandContext, task_name_or_alias: str, list_name: str | None = None
    ) -> None:
        info = ctx.services.task_query.get_info(
            FieldSlotStr(task_name_or_alias),
            DEFAULT if list_name is None else ListNameStr(list_name),
        )

        await messages.object_info(
            ctx.interaction,
            info.task,
            {
                str(attr.name): tuple(map(formatting.typed_slot_to_str, field))
                for attr, field in info.data.items()
            },
        )

    @app_commands.command()
    @with_context()
    async def create(
        self,
        ctx: CommandContext,
        task_name: str,
        list_name: str,
        aliases_dsl_sequence: str,
        field_mapping_dsl: str,
    ) -> None:
        task = ctx.services.task.create(
            FieldSlotStr(task_name),
            ListNameStr(list_name),
            bindings.sequence.task_aliases(aliases_dsl_sequence),
            bindings.mapping.field_mapping(field_mapping_dsl),
        )

        await messages.object_created(ctx.interaction, task)

    @app_commands.command()
    @with_context()
    async def nuke(self, ctx: CommandContext, task_name: str, list_name: str) -> None:
        prepared, lst, task = ctx.services.task_prepare.delete(
            FieldSlotStr(task_name), ListNameStr(list_name)
        )

        await messages.nuke_object_on_confirmation(
            ctx.interaction,
            to_nuke=task,
            parent=lst,
            consequences=t"All its associated field and user field data will be deleted!",
            execute=lambda: ctx.services.task.delete(prepared),
        )

    @edit_group.command(name="name")
    @with_context()
    async def edit_name(
        self,
        ctx: CommandContext,
        task_name: str,
        new_task_name: str,
        list_name: str,
    ) -> None:
        after = FieldSlotStr(new_task_name)
        before = ctx.services.task.edit_name(
            FieldSlotStr(task_name), after, ListNameStr(list_name)
        )

        await messages.object_name_edited(ctx.interaction, Concept.TASK, before, after)

    @edit_group.command(name="aliases")
    @with_context()
    async def edit_aliases(
        self,
        ctx: CommandContext,
        task_name: str,
        new_task_aliases_dsl_sequence: str,
        list_name: str,
        edit_mode: AliasEditModeInterfaceEnum,
    ) -> None:
        after = bindings.sequence.task_aliases(new_task_aliases_dsl_sequence)
        task = ctx.services.task.edit_aliases(
            after,
            AliasEditMode(edit_mode.value),
            FieldSlotStr(task_name),
            ListNameStr(list_name),
        )

        await messages.object_aliases_edited(ctx.interaction, task)

    @edit_group.command(name="field_mapping")
    @with_context()
    async def edit_field_mapping(
        self,
        ctx: CommandContext,
        task_name: str,
        list_name: str,
        new_field_mapping_dsl: str,
        edit_mode: FieldMappingEditModeInterfaceEnum,
    ) -> None:
        task = ctx.services.task.edit_field_mapping(
            bindings.mapping.field_mapping(new_field_mapping_dsl),
            FieldMappingEditMode(edit_mode.value),
            FieldSlotStr(task_name),
            DEFAULT if list_name is None else ListNameStr(list_name),
        )

        await messages.success(
            ctx.interaction,
            t"{F.format(Concept.TASK)} {F.format(Concept.FIELD_MAPPING)} Edited",
            t"The field mapping of the {F.full_mention(task)} was successfully edited!",
        )

    # --- Member Task --- #

    @app_commands.command()
    @with_context()
    async def info_user(
        self,
        ctx: CommandContext,
        task_name_or_alias: str,
        user: discord.User | None = None,
        list_name: str | None = None,
    ) -> None:
        info = ctx.services.member_task_query.get_info(
            FieldSlotStr(task_name_or_alias),
            user_ref.user_ref(user),
            DEFAULT if list_name is None else ListNameStr(list_name),
        )

        await messages.object_info(
            ctx.interaction,
            info.task,
            {
                str(attr.name): tuple(map(formatting.typed_slot_to_str, field))
                for attr, field in info.data.items()
            },
        )

    @app_commands.command()
    @with_context()
    async def give(
        self,
        ctx: CommandContext,
        task_name_or_alias: str,
        user_field_mapping_dsl: str | None = None,
        user: discord.User | None = None,
        list_name: str | None = None,
    ) -> None:
        member, task = ctx.services.member_task.give_to_user(
            FieldSlotStr(task_name_or_alias),
            DEFAULT if list_name is None else ListNameStr(list_name),
            bindings.mapping.field_mapping(user_field_mapping_dsl),
            user_ref.user_ref(user),
        )

        await messages.success(
            ctx.interaction,
            t"{F.format(Concept.TASK)} Given",
            t"The {F.full_mention(task)} has been given to the {F.full_mention(member)} successfully!",
        )

    @app_commands.command()
    @with_context()
    async def take(
        self,
        ctx: CommandContext,
        task_name_or_alias: str,
        user: discord.User | None = None,
        list_name: str | None = None,
    ) -> None:
        member, task = ctx.services.member_task.take_from_user(
            FieldSlotStr(task_name_or_alias),
            DEFAULT if list_name is None else ListNameStr(list_name),
            user_ref.user_ref(user),
        )

        await messages.success(
            ctx.interaction,
            t"{F.format(Concept.TASK)} Taken",
            t"The {F.full_mention(task)} has been taken from the {F.full_mention(member)} successfully!",
        )

    @edit_group.command(name="given")
    @with_context()
    async def edit_given(
        self,
        ctx: CommandContext,
        task_name_or_alias: str,
        new_user_field_mapping: str,
        edit_mode: FieldMappingEditModeInterfaceEnum,
        user: discord.User | None = None,
        list_name: str | None = None,
    ) -> None:
        member, task = ctx.services.member_task.edit_member_field_mapping(
            bindings.mapping.field_mapping(new_user_field_mapping),
            FieldMappingEditMode(edit_mode.value),
            user_ref.user_ref(user),
            FieldSlotStr(task_name_or_alias),
            DEFAULT if list_name is None else ListNameStr(list_name),
        )

        await messages.success(
            ctx.interaction,
            t"Given {F.format(Concept.TASK)} Updated",
            t"The {F.full_mention(task)} the {F.full_mention(member)} had already given themselves was updated successfully!",
        )


class TasksInterface(
    BaseInterface, group_name=cogs.cog_concept_to_group_name(Concept.TASK, plural=True)
):
    @app_commands.command()
    @with_context()
    async def browse(
        self,
        ctx: CommandContext,
        filter_dsl: str | None = None,
        sort_dsl: str | None = None,
        yield_dsl_sequence: str | None = None,
        list_name: str | None = None,
    ) -> None:
        summaries = ctx.services.task_query.get_summaries(
            bindings.filter.filter(filter_dsl),
            bindings.sort.sorts(sort_dsl),
            bindings.sequence.yield_(yield_dsl_sequence),
            DEFAULT if list_name is None else ListNameStr(list_name),
        )

        await messages.object_browse(
            ctx.interaction,
            Concept.TASK,
            {
                str(attr.name): tuple(
                    tuple(map(formatting.typed_slot_to_str, field)) for field in fields
                )
                for attr, fields in summaries.items()
            },
        )

    # --- Member Task --- #

    @app_commands.command()
    @with_context()
    async def browse_user(
        self,
        ctx: CommandContext,
        user: discord.User | None = None,
        filter_dsl: str | None = None,
        sort_dsl: str | None = None,
        yield_dsl_sequence: str | None = None,
        list_name: str | None = None,
    ) -> None:
        summaries = ctx.services.member_task_query.get_summaries(
            bindings.filter.filter(filter_dsl),
            bindings.sort.sorts(sort_dsl),
            bindings.sequence.yield_(yield_dsl_sequence),
            user_ref.user_ref(user),
            DEFAULT if list_name is None else ListNameStr(list_name),
        )

        await messages.object_browse(
            ctx.interaction,
            Concept.TASK,
            {
                str(attr.name): tuple(
                    tuple(map(formatting.typed_slot_to_str, field)) for field in fields
                )
                for attr, fields in summaries.items()
            },
        )

    @app_commands.command()
    @with_context()
    async def browse_missing(
        self,
        ctx: CommandContext,
        user: discord.User | None = None,
        filter_dsl: str | None = None,
        sort_dsl: str | None = None,
        yield_dsl_sequence: str | None = None,
        list_name: str | None = None,
    ) -> None:
        summaries = ctx.services.member_task_query.get_summaries_missing(
            bindings.filter.filter(filter_dsl),
            bindings.sort.sorts(sort_dsl),
            bindings.sequence.yield_(yield_dsl_sequence),
            user_ref.user_ref(user),
            DEFAULT if list_name is None else ListNameStr(list_name),
        )

        await messages.object_browse(
            ctx.interaction,
            Concept.TASK,
            {
                str(attr.name): tuple(
                    tuple(map(formatting.typed_slot_to_str, field)) for field in fields
                )
                for attr, fields in summaries.items()
            },
        )

    # --- Bulk --- #

    def _parse_bulk_line(self, line: str) -> tuple[str, frozendict[str, str]]:
        for cmd in self.bot.tree.walk_commands():
            name = cmd.qualified_name

            if name not in _BULK_COMMANDS:
                continue

            if line != f"/{name}" and not line.startswith(f"/{name} "):
                continue

            assert isinstance(cmd, app_commands.Command)

            # Same format Discord accepts when a command is pasted into the chat:
            # an option starts at its name followed by a colon.
            before, *names_and_values = re.split(
                rf"(?:^|(?<=\s))({'|'.join(param.name for param in cmd.parameters)}):",
                line.removeprefix(f"/{name}"),
            )

            if before.strip():
                raise TextBeforeFirstCommandOption(before.strip())

            options: dict[str, str] = {}

            for option, value in itertools.batched(names_and_values, 2, strict=True):
                if option in options:
                    raise CommandOptionMentionedMoreThanOnce(option)

                options[option] = value.strip()

            for param in cmd.parameters:
                if param.name not in options:
                    if param.required:
                        raise CommandOptionNotMentioned(param.name)

                    continue

                choices = tuple(choice.name for choice in param.choices)

                if choices and options[param.name] not in choices:
                    raise UnknownCommandOptionChoice(param.name, choices)

            return name, frozendict(options)

        raise NotABulkCommand(_BULK_COMMANDS)

    @app_commands.command()
    @with_context()
    async def bulk(self, ctx: CommandContext, file: discord.Attachment) -> None:
        lines: list[tuple[int, str]] = []

        for i, text in enumerate(
            (await bindings.attachment.text(file)).splitlines(), start=1
        ):
            text = text.strip()

            # Empty lines and comments are skipped.
            if text and not text.startswith("#"):
                lines.append((i, text))

        if not lines:
            raise NoCommandsInFile()

        number: int = 0
        line: str = ""

        try:
            # All users are fetched before the first command is executed, so no row
            # stays locked while waiting for Discord.
            mention_to_user: dict[str, discord.User] = {}
            commands: list[_BulkCommand] = []

            for number, line in lines:
                name, options = self._parse_bulk_line(line)
                mention = options.get("user")

                if mention is not None and mention not in mention_to_user:
                    mention_to_user[mention] = await user_ref.user_from_mention(
                        self.bot, mention
                    )

                commands.append(
                    _BulkCommand(
                        name,
                        options,
                        None if mention is None else mention_to_user[mention],
                    )
                )

            command_counts: dict[str, int] = {}

            for command in commands:
                command_counts[command.name] = command_counts.get(command.name, 0) + 1

            if not await messages.bulk_confirmation(ctx.interaction, command_counts):
                return

            for (number, line), command in zip(lines, commands, strict=True):
                _execute_bulk_command(ctx, command)

        except (BusinessError, DslError) as e:
            # Shown below the reason in the error message.
            e.add_note(
                f"The command {formatting.embed(formatting.shorten(line))} in line {number} of the file failed, so no command of the file was executed!"
            )
            raise

        await messages.success(
            ctx.interaction,
            t"Bulk Executed",
            t"All commands of the file were executed successfully!\n"
            + t"Commands executed: {F.string(str(len(commands)), embedded=False)}",
        )
