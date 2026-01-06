import builtins
import enum
import typing as t
from collections import deque
from string.templatelib import Interpolation, Template
from types import EllipsisType

import discord as dc
import discord.app_commands as acmds
import discord.ext.commands as cmds

from adapters import parsing
from adapters.interaction import InteractionAdapter
from discord_.errors import FeedbackError
from discord_.utils_ import messaging, shortcuts
from structures.attribute import AnyAttributeT, StaticAttribute
from structures.attribute.slot_str import SlotStr
from structures.list import Kind
from utils import gist
from utils.expression_parsing.errors import BaseExpressionParsingError
from utils.rank import CommunityRank
from utils.text import NormStr

from ..utils_ import predicate
from ..utils_ import user as user_

_ESCAPE_TABLE: t.Final[dict[t.Any, str]] = str.maketrans(
    {char: rf"\{char}" for char in r"$&\`*_~#+-.!|()[]{}<>"}
)
_DELIM: t.Final[str] = "|"
_DIV: t.Final[str] = ":---"


def _escape_cell(c: tuple[str, ...], /) -> str:
    if not c:
        return ""

    global _ESCAPE_TABLE

    if "`" in c:
        return "<br/>".join(f"<code>{s.translate(_ESCAPE_TABLE)}</code>" for s in c)

    return "<br/>".join(f"`{s}`".replace("|", r"\|") for s in c)


class RowToStrMode(enum.Enum):
    HEADER = enum.auto()
    DIVIDER = enum.auto()
    BODY = enum.auto()


def _row_to_str(
    row: t.Iterable[tuple[str, ...]],
    mode: RowToStrMode = RowToStrMode.BODY,
    # pos: int = 0,
) -> str:
    if mode is RowToStrMode.BODY:
        # {_DELIM}**{pos}**
        return f"{_DELIM}{_DELIM.join(map(_escape_cell, row))}"

    if mode is RowToStrMode.HEADER:
        # {_DELIM}**#**
        return f"{_DELIM}{_DELIM.join(map(_escape_cell, row))}"

    if mode is RowToStrMode.DIVIDER:
        # {_DELIM}{_DIV}
        return f"{_DELIM}{_DELIM.join(map('<br/>'.join, row))}"

    t.assert_never(mode)


def _task_data_table_to_gist_files(
    table: t.Iterable[t.Iterable[tuple[str, ...]]],
    headers: t.Sequence[str] | None = None,
    *,
    soft_split_limit: int = 1_000_000,
) -> list[str]:
    result: list[str] = []

    curr_rows: deque[str] = deque()
    char_count: int = 0

    headers_str_rev: tuple[str, str] | tuple[()] = ()

    if headers is not None:
        headers_str_rev = (
            _row_to_str(((_DIV,) for _ in range(len(headers))), RowToStrMode.DIVIDER),
            _row_to_str(((h,) for h in headers), RowToStrMode.HEADER),
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


async def _info(
    interaction: dc.Interaction,
    task: str,
    user: dc.User | None | EllipsisType,
    list: str | None,
) -> None:
    list_obj = shortcuts.get_specified_or_selected_or_default_list(
        InteractionAdapter(interaction), None, list
    )

    avm = list_obj.get_task(task).get_attribute_value_mapping(
        None
        if user is ...
        else shortcuts.get_or_create_specified_or_current_community_user(
            list_obj.community, user
        )
    )

    elems: builtins.list[str | Interpolation] = []

    for attr, v in avm.combined.items():
        elems.append(Interpolation(f"**{attr.name.replace('*', r'\*')}**: "))

        if not v:
            elems.append(str(...))
        else:
            elems.append(f"{messaging.embed_join(*v)}")

        elems.append("\n")

    if elems:
        elems.pop()

    await interaction.response.send_message(
        messaging.layout(
            "Task Info",
            Template(*elems),
            message_status=messaging.MessageStatus.INFO,
        )
    )


class Yield(enum.Enum):
    DEFAULT = enum.auto()
    ONLY_NAME = enum.auto()
    ALL = enum.auto()


async def _browse(
    interaction: dc.Interaction,
    filter: str | None,
    sort: str | None,
    yield_: Yield,
    user: dc.User | None | EllipsisType,
    missing: bool,
    list: str | None,
) -> None:
    assert missing is (user is not Ellipsis)

    # Get the list of the executing user, not the specified user
    list_obj = shortcuts.get_specified_or_selected_or_default_list(
        InteractionAdapter(interaction), None, list
    )

    community_user = shortcuts.get_or_create_specified_or_current_community_user(
        list_obj.community, None if user is ... else user
    )

    await interaction.response.defer()
    msg = t.cast(
        dc.Message,
        await interaction.followup.send("Retrieving data...", suppress_embeds=True),
    )

    ATTRIBUTE_TYPES_TO_HANDLE: tuple[type[AnyAttributeT], ...]

    # --- Get attribute value mapping of jumpedia or user ---
    if user is Ellipsis:
        avms, attrs, ATTRIBUTE_TYPES_TO_HANDLE = (
            list_obj._s.get_task_attribute_value_mappings(None)
        )
    else:
        user_task_ids = tuple(
            task._s.id for task in list_obj.get_tasks_of_user(community_user)
        )

        task_ids_to_fetch: tuple[int, ...]

        if not missing:
            task_ids_to_fetch = user_task_ids
        else:
            task_ids_to_fetch = tuple(
                set(task.id for task in list_obj.get_tasks()).difference(user_task_ids)
            )

        # Don't include user attribute values when missing, because those don't have any values, because well they are missing
        avms, attrs, ATTRIBUTE_TYPES_TO_HANDLE = (
            list_obj._s.get_task_attribute_value_mappings(
                None if missing else community_user._s.id, task_ids_to_fetch
            )
        )

    ATTRS_SORTED: t.Final[tuple[AnyAttributeT, ...]] = tuple(
        sorted(attrs, key=lambda a: a.position)
    )

    del attrs

    NAME_ATTR: AnyAttributeT | None = None

    for attr in ATTRS_SORTED:
        if isinstance(attr, StaticAttribute) and attr.kind is Kind.NAME:
            NAME_ATTR = attr
            break

    assert NAME_ATTR is not None

    # --- Filter, Sort and other... --
    used_attributes: set[AnyAttributeT] = set()
    syn_to_attr: dict[NormStr, AnyAttributeT] = {}

    if filter or sort:
        for attr_type in ATTRIBUTE_TYPES_TO_HANDLE:
            for alias, attr in list_obj._s.get_attribute_alias_mapping(
                attr_type
            ).items():
                syn_to_attr[NormStr(alias)] = attr

            syn_to_attr |= {attr.norm_name: attr for attr in ATTRS_SORTED}

    # - Filter -
    if filter:
        await msg.edit(content="Filtering data...")

        try:
            avms, filter_used_attributes = parsing.FilterStringParser().parse(
                filter,
                avms,
                syn_to_attr,
            )
        except BaseExpressionParsingError:
            raise FeedbackError(
                "Invalid Filter Syntax",
                t"The syntax specified for the filter is invalid.",
            )

        used_attributes |= filter_used_attributes

    if not avms:
        raise FeedbackError(
            "No Matching Tasks",
            t"There is no task that matches the specified criteria!",
        )

    # - Sort -
    await msg.edit(content="Sorting data...")

    if not sort:
        avms = parsing.sort(avms, [(NAME_ATTR, True)])
    else:
        try:
            avms = parsing.SORT_PARSER.parse(sort, avms, syn_to_attr)
        except BaseExpressionParsingError:
            raise FeedbackError(
                "Invalid Sort Syntax", t"The syntax specified for the sort is invalid."
            )

    del syn_to_attr

    # --- Convert to text ---
    await msg.edit(content="Converting data into text...")

    # - Yield -
    attribute_yield: set[AnyAttributeT]

    if yield_ is Yield.DEFAULT:
        attribute_yield = {NAME_ATTR} | used_attributes
    elif yield_ is Yield.ONLY_NAME:
        attribute_yield = {NAME_ATTR}
    elif yield_ is Yield.ALL:
        attribute_yield = set(ATTRS_SORTED)
    else:
        t.assert_never(yield_)

    table: tuple[tuple[tuple[SlotStr, ...], ...], ...] = tuple(
        tuple(
            avm.combined.get(attr, ())
            for attr in ATTRS_SORTED
            if attr in attribute_yield
        )
        for avm in avms
    )

    files = _task_data_table_to_gist_files(
        table, tuple(attr.real_name for attr in ATTRS_SORTED if attr in attribute_yield)
    )

    # --- Data to gists ---
    await msg.edit(content="Sending text to GitHub gist...")

    urls = tuple(
        gist.create_gist({f"Task Data #{str(i).zfill(3)}.md": file})
        for i, file in enumerate(files, 1)
    )

    # --- Success ---
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

    @acmds.command()
    async def info(
        self, interaction: dc.Interaction, task: str, list: str | None = None
    ) -> None:
        await _info(interaction, task, ..., list)

    @acmds.command()
    async def info_user(
        self,
        interaction: dc.Interaction,
        task: str,
        user: dc.User | None = None,
        list: str | None = None,
    ) -> None:
        await _info(interaction, task, user, list)

    @acmds.command()
    @acmds.rename(yield_="yield")
    async def browse(
        self,
        interaction: dc.Interaction,
        filter: str | None = None,
        sort: str | None = None,
        yield_: Yield = Yield.DEFAULT,
        list: str | None = None,
    ) -> None:
        await _browse(interaction, filter, sort, yield_, ..., False, list)

    @acmds.command()
    @acmds.rename(yield_="yield")
    async def browse_user(
        self,
        interaction: dc.Interaction,
        filter: str | None = None,
        sort: str | None = None,
        yield_: Yield = Yield.DEFAULT,
        user: dc.User | None = None,
        list: str | None = None,
    ) -> None:
        await _browse(interaction, filter, sort, yield_, user, False, list)

    @acmds.command()
    @acmds.rename(yield_="yield")
    async def browse_missing(
        self,
        interaction: dc.Interaction,
        filter: str | None = None,
        sort: str | None = None,
        yield_: Yield = Yield.DEFAULT,
        user: dc.User | None = None,
        list: str | None = None,
    ) -> None:
        await _browse(interaction, filter, sort, yield_, user, True, list)

    @acmds.command()
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
                t"The task {task.name:c} has successfully been created!",
                messaging.MessageStatus.SUCCESS,
            )
        )

    @acmds.command()
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
                t"The task {task:c} has successfully been deleted!",
                messaging.MessageStatus.SUCCESS,
            )
        )

    @acmds.command()
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
                t"The task {task_obj.name:c} has successfully been given to {community_user.name:c}!",
                messaging.MessageStatus.SUCCESS,
            )
        )
