from utils.expression_parsing.errors import BaseExpressionParsingError
import builtins
import pprint
import typing as t
from collections import deque
from string.templatelib import Interpolation, Template
from types import EllipsisType

import discord as dc
import discord.app_commands as acmds
import discord.ext.commands as cmds
from attr import frozen
from docutils.nodes import header

from adapters import parsing
from adapters.interaction import InteractionAdapter
from discord_.errors import FeedbackError
from discord_.utils_ import messaging, shortcuts
from structures.attribute import AnyAttributeT
from structures.attribute.slot_str import SlotStr
from structures.task.attribute_value_mapping import (
    AttributeValueMapping,
    UserAttributeValueMapping,
)
from utils import gist
from utils.rank import CommunityRank
from utils.text import NormStr

from ..utils_ import predicate
from ..utils_ import user as user_

_ESCAPE_TABLE: t.Final[dict[t.Any, str]] = str.maketrans(
    {char: rf"\{char}" for char in r"$&\`*_~#+-.!|()[]{}<>"}
)
_DELIM: t.Final[str] = "|"


def _escape_cell(c: tuple[str, ...], /) -> str:
    if not c:
        return ""

    global _ESCAPE_TABLE

    if "`" in c:
        return "<br/>".join(f"<code>{s.translate(_ESCAPE_TABLE)}</code>" for s in c)

    return "<br/>".join(f"`{s}`".replace("|", r"\|") for s in c)


def _row_to_str(row: t.Iterable[tuple[str, ...]], raw: bool = False) -> str:
    return f"{_DELIM}{_DELIM.join(map('<br/>'.join, row) if raw else map(_escape_cell, row))}{_DELIM}"


def _task_data_table_to_gist_files(
    table: t.Iterable[t.Iterable[tuple[str, ...]]],
    headers: t.Sequence[str] | None = None,
    *,
    soft_split_limit: int = 500_000,
) -> list[str]:
    result: list[str] = []

    curr_rows: deque[str] = deque()
    char_count: int = 0

    headers_str_rev: tuple[str, str] | tuple[()] = ()

    if headers is not None:
        headers_str_rev = (
            _row_to_str(((":---",) for _ in range(len(headers))), True),
            _row_to_str((h,) for h in headers),
        )

    del headers

    for row in table:
        row_str = _row_to_str(row)

        del row

        char_count += len(row_str)

        curr_rows.append(row_str)

        if char_count >= soft_split_limit:
            curr_rows.extendleft(headers_str_rev)
            result.append("\n".join(curr_rows))

            curr_rows.clear()
            char_count = 0

    if curr_rows:
        curr_rows.extendleft(headers_str_rev)
        result.append("\n".join(curr_rows))

    return result


async def _browse(
    interaction: dc.Interaction,
    filter: str | None,
    sort: str | None,
    user: dc.User | None | EllipsisType,
    list: str | None,
) -> None:
    community_user = shortcuts.get_or_create_specified_or_current_community_user(
        InteractionAdapter(interaction), None if user is Ellipsis else user
    )

    list_obj = shortcuts.get_specified_or_selected_or_default_list(community_user, list)

    await interaction.response.defer()

    msg = await interaction.followup.send("Retrieving data...", suppress_embeds=True)

    if user is Ellipsis:
        avms, attrs = list_obj._s.get_task_attribute_value_mappings(None)
    else:
        user_task_ids = tuple(
            task._s.id for task in list_obj.get_tasks_of_user(community_user)
        )

        avms, attrs = list_obj._s.get_task_attribute_value_mappings(
            community_user._s.id, user_task_ids
        )

    ATTRS_SORTED: t.Final[tuple[AnyAttributeT, ...]] = tuple(
        sorted(attrs, key=lambda a: a.position)
    )

    used_attributes: set[AnyAttributeT] = set()

    if filter:
        await msg.edit(content="Filtering data...")

        syn_to_attr: dict[NormStr, AnyAttributeT] = {}

        if attrs:
            for alias, attr in list_obj._s.get_all_attribute_alias_mappings(
                *(attr.id for attr in attrs)
            ).items():
                syn_to_attr[NormStr(alias)] = attr

            syn_to_attr |= {attr.norm_name: attr for attr in attrs}

        try:
            avms = parsing.FILTER_PARSER.parse(
                filter,
                avms,
                syn_to_attr,
                used_attributes
            )
        except BaseExpressionParsingError:
            raise FeedbackError(
                "Invalid Filter Syntax",
                t"The syntax specified for the filter is invalid."
            )
    
    if not avms:
        raise FeedbackError(
            "No Matching Tasks",
            t"There is no task that matches the specified criteria!",
        )

    if sort:
        await msg.edit(content="Sorting data...")

        try:
            avms = parsing.SORT_VISITOR.parse(
                sort,
                avms,
                syn_to_attr,
                used_attributes
            )
        except BaseExpressionParsingError:
            raise FeedbackError(
                "Invalid Sort Syntax",
                t"The syntax specified for the sort is invalid."
            )

    await msg.edit(content="Converting data into text...")

    table: tuple[tuple[tuple[SlotStr, ...], ...], ...] = tuple(
        tuple(avm.combined.get(attr, ()) for attr in ATTRS_SORTED) for avm in avms
    )

    files = _task_data_table_to_gist_files(
        table, tuple(attr.real_name for attr in ATTRS_SORTED)
    )

    await msg.edit(content="Sending data to GitHub gist...")

    urls = tuple(
        gist.create_gist({f"Task Data #{str(i).zfill(3)}.md": file})
        for i, file in enumerate(files, 1)
    )

    await msg.edit(
        content=messaging.layout(
            "All Tasks",
            Template(
                "\n".join(
                    f"- **#{str(i).zfill(3)}**: {url}" for i, url in enumerate(urls, 1)
                )
                if len(urls) > 1
                else urls[0]
            ),
            messaging.MessageStatus.INFO,
        ),
    )


class TaskCog(cmds.GroupCog, group_name="task"):
    def __init__(self, bot: cmds.Bot) -> None:
        self.bot = bot

    @acmds.command(description="Get information about a task.")
    async def info(
        self, interaction: dc.Interaction, task: str, list: str | None = None
    ) -> None:
        list_obj = shortcuts.get_specified_or_selected_or_default_list(
            InteractionAdapter(interaction), None, list
        )

        avm = list_obj.get_task(task).get_attribute_value_mapping(
            shortcuts.get_or_create_specified_or_current_community_user(
                list_obj.community, None
            )
        )

        elems: builtins.list[str | Interpolation] = []

        for attr, v in avm.combined.items():
            elems.append(Interpolation(f"**{attr.name.replace('*', '\\*')}**: "))

            if not v:
                elems.append(str(None))
            else:
                elems.append(f"`{'`, `'.join(v)}`")

            elems.append("\n")

        elems.pop()

        await interaction.response.send_message(
            messaging.layout(
                "Task Info",
                Template(*elems),
                message_status=messaging.MessageStatus.INFO,
            )
        )

    browse_group = acmds.Group(name="browse", description="Browse tasks.")

    @browse_group.command(name="all", description="Browse all tasks.")
    async def browse_all(
        self,
        interaction: dc.Interaction,
        filter: str | None = None,
        sort: str | None = None,
        list: str | None = None,
    ) -> None:
        await _browse(interaction, filter, sort, ..., list)

    @browse_group.command(name="user", description="Browse all tasks of a user.")
    async def browse_user(
        self,
        interaction: dc.Interaction,
        filter: str | None = None,
        sort: str | None = None,
        user: dc.User | None = None,
        list: str | None = None,
    ) -> None:
        await _browse(interaction, filter, sort, user, list)

    @acmds.command(description="Create a new task.")
    @acmds.check(predicate.rank_required(CommunityRank.HELPER))
    async def create(
        self,
        interaction: dc.Interaction,
        name: str,
        aliases: str | None = None,
        attribute_value_mapping: str | None = None,
        list: str | None = None,
    ) -> None:
        list_obj = shortcuts.get_specified_or_selected_or_default_list(
            InteractionAdapter(interaction), None, list
        )

        task = list_obj.create_task(name, aliases, attribute_value_mapping)

        await interaction.response.send_message(
            messaging.layout(
                "Task Created",
                t"The task `{task.name}` has successfully been created!",
                messaging.MessageStatus.SUCCESS,
            )
        )

    @acmds.command(description="Delete an existing task.")
    @acmds.check(predicate.rank_required(CommunityRank.MODERATOR))
    async def nuke(
        self, interaction: dc.Interaction, task: str, list: str | None = None
    ) -> None:
        list_obj = shortcuts.get_specified_or_selected_or_default_list(
            InteractionAdapter(interaction), None, list
        )

        list_obj.delete_task(task)

        await interaction.response.send_message(
            messaging.layout(
                "Task Delete",
                t"The task `{task}` has successfully been deleted!",
                messaging.MessageStatus.SUCCESS,
            )
        )

    @acmds.command(description="Give a task to a user.")
    async def give(
        self,
        interaction: dc.Interaction,
        task: str,
        user_attribute_value_mapping: str | None = None,
        user: dc.User | None = None,
        list: str | None = None,
    ) -> None:
        user_.validate_allowed_for_others(interaction, user, CommunityRank.MODERATOR)

        community_user = shortcuts.get_or_create_specified_or_current_community_user(
            InteractionAdapter(interaction), user
        )
        list_obj = shortcuts.get_specified_or_selected_or_default_list(
            community_user, list
        )

        task_obj = list_obj.give_task_to_user(
            task, community_user, user_attribute_value_mapping
        )

        await interaction.response.send_message(
            messaging.layout(
                "Task Given",
                t"The task `{task_obj.name}` has successfully been given to `{community_user.name}`!",
                messaging.MessageStatus.SUCCESS,
            )
        )
