import builtins
import enum
import typing as t
from collections import deque
from string.templatelib import Interpolation, Template
from types import CoroutineType, EllipsisType

import discord as dc
import discord.app_commands as acmds
import discord.ext.commands as cmds

import dc_utils
from adapting import parsing
from adapting.interaction import InteractionAdapter
from dc_utils import command, layouts, message, predicate, shortcuts
from dc_utils.errors import FeedbackError
from dc_utils.rank import CommunityRank
from structures.attribute import AnyAttributeT, StaticAttribute
from structures.attribute.slot_str import SlotStr
from structures.list import Kind
from structures.task import Task
from structures.task.attribute_value_mapping import (
    AttributeValueMapping,
    UserAttributeValueMapping,
)
from utils import gist
from utils.text import NormStr, RealStr


async def _info(
    ia: InteractionAdapter,
    task: str,
    user: dc.User | None | EllipsisType,
    list: str | None,
) -> None:
    list_obj = shortcuts.get_specified_or_selected_or_default_list(ia, None, list)

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
            elems.append(f"{message.embed_join(*v)}")

        elems.append("\n")

    if elems:
        elems.pop()

    await ia.dc.response.send_message(
        message.layout(
            "Task Info",
            Template(*elems),
            message_status=message.MessageStatus.INFO,
        )
    )


class Yield(enum.Enum):
    DEFAULT = enum.auto()
    ONLY_NAME = enum.auto()
    ALL = enum.auto()


async def _browse(
    ia: InteractionAdapter,
    filter: str | None,
    sort: str | None,
    yield_: Yield,
    user: dc.User | None | EllipsisType,
    missing: bool,
    list: str | None,
) -> CoroutineType[None, None, t.Any]:
    assert missing is (user is not Ellipsis)

    finished_content: str = ""
    prev_content: str = ""

    def update_loading(s: str) -> str:
        nonlocal finished_content, prev_content

        if prev_content:
            finished_content += f"✅ {prev_content}\n"

        prev_content = s

        return finished_content + f"⚙️ {s}"

    # Get the list of the executing user, not the specified user
    list_obj = shortcuts.get_specified_or_selected_or_default_list(ia, None, list)

    community_user = shortcuts.get_or_create_specified_or_current_community_user(
        list_obj.community, None if user is ... else user
    )

    await ia.dc.response.defer()

    msg = t.cast(
        dc.Message,
        await ia.dc.followup.send(
            update_loading("Retrieving data..."), suppress_embeds=True
        ),
    )

    ATTRIBUTE_TYPES_TO_HANDLE: tuple[type[AnyAttributeT], ...]

    avms: list[AttributeValueMapping] | list[UserAttributeValueMapping]

    # --- Get attribute value mapping of jumpedia or user ---
    if user is Ellipsis:
        avms, attrs, ATTRIBUTE_TYPES_TO_HANDLE = (
            list_obj._o.get_attribute_value_mappings(ia._c, None)
        )
    else:
        user_task_ids = tuple(
            task._o.id for task in list_obj.get_tasks_of_user(community_user)
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
            list_obj._o.get_attribute_value_mappings(
                ia._c, None if missing else community_user._o.id, task_ids_to_fetch
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
        syn_to_attr = {
            NormStr(k): v
            for k, v in list_obj._o.get_attributes_by_syn(
                ia._c, ..., type=ATTRIBUTE_TYPES_TO_HANDLE
            ).items()
        }

    # - Filter -
    if filter:
        await msg.edit(content=update_loading("Filtering data..."))

        avms, filter_used_attributes = parsing.filter.parse(
            ia._c,
            RealStr(filter),
            avms,
            syn_to_attr,
        )

        used_attributes |= filter_used_attributes

        del filter_used_attributes

    if not avms:
        return msg.edit(
            content=layouts.info(
                "Tasks Browsed",
                t"No tasks that match the specified criteria have been found!",
            )
        )

    # - Sort -
    await msg.edit(content=update_loading("Sorting data..."))

    if not sort:
        avms = parsing.sort.sort(ia._c, avms, [(NAME_ATTR, True)])
        sort_used_attributes = {NAME_ATTR}
    else:
        avms, sort_used_attributes = parsing.sort.parse(
            ia._c, RealStr(sort), avms, syn_to_attr
        )

    used_attributes |= sort_used_attributes

    del syn_to_attr, sort_used_attributes

    # --- Convert to text ---
    await msg.edit(content=update_loading("Converting data into text..."))

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

    tasks = tuple(avm.task for avm in avms)
    
    return command.browse(
        ia,
        Task,
        rows=tuple(
            tuple(
                avm.combined.get(attr, ())  # type: ignore
                for attr in ATTRS_SORTED
                if attr in attribute_yield
            )
            for avm in avms
        ),
        headers=tuple(
            attr.real_name for attr in ATTRS_SORTED if attr in attribute_yield
        ),
        before_send=lambda strings: msg.edit(
            content=update_loading(
                f"Sending text to GitHub Gist... ({sum(map(len, strings)):,} Bytes across {len(strings)} file{'s' if len(strings) > 1 else ''})"
            )
        ),
    )

    # --- Success ---
    return msg.edit(content=layout)


class TaskCog(cmds.GroupCog, group_name="task"):
    def __init__(self, bot: cmds.Bot) -> None:
        self.bot = bot

    @acmds.command()
    @command.adapt
    async def info(
        self, ia: InteractionAdapter, task: str, list: str | None = None
    ) -> CoroutineType[None, None, t.Any]:
        return _info(ia, task, ..., list)

    @acmds.command()
    @command.adapt
    async def info_user(
        self,
        ia: InteractionAdapter,
        task: str,
        user: dc.User | None = None,
        list: str | None = None,
    ) -> CoroutineType[None, None, t.Any]:
        return _info(ia, task, user, list)

    @acmds.command()
    @acmds.check(predicate.rank_required(CommunityRank.HELPER))
    @command.adapt
    async def create(
        self,
        ia: InteractionAdapter,
        name: str,
        aliases: str | None = None,
        attribute_value_mapping: str | None = None,
        list: str | None = None,
    ) -> CoroutineType[None, None, t.Any]:
        list_obj = shortcuts.get_specified_or_selected_or_default_list(ia, None, list)

        task = list_obj.create_task(name, aliases, attribute_value_mapping)

        return ia.dc.response.send_message(
            message.layout(
                "Task Created",
                t"The task {task.name:,} has successfully been created!",
                message.MessageStatus.SUCCESS,
            )
        )

    @acmds.command()
    @acmds.check(predicate.rank_required(CommunityRank.MODERATOR))
    @command.adapt
    async def nuke(
        self, ia: InteractionAdapter, task: str, list: str | None = None
    ) -> CoroutineType[None, None, t.Any]:
        list_obj = shortcuts.get_specified_or_selected_or_default_list(ia, None, list)

        list_obj.delete_task(task)

        return ia.dc.response.send_message(
            message.layout(
                "Task Delete",
                t"The task {task:,} has successfully been deleted!",
                message.MessageStatus.SUCCESS,
            )
        )

    @acmds.command()
    @command.adapt
    async def give(
        self,
        ia: InteractionAdapter,
        task: str,
        user_attribute_value_mapping: str | None = None,
        user: dc.User | None = None,
        list: str | None = None,
    ) -> CoroutineType[None, None, t.Any]:
        dc_utils.user.validate_allowed_for_others(ia.dc, user, CommunityRank.MODERATOR)

        community_user = shortcuts.get_or_create_specified_or_current_community_user(
            ia, user
        )
        list_obj = shortcuts.get_specified_or_selected_or_default_list(
            community_user, list
        )

        task_obj = list_obj.give_task_to_user(
            task, community_user, user_attribute_value_mapping
        )

        return ia.dc.response.send_message(
            message.layout(
                "Task Given",
                t"The task {task_obj.name:,} has successfully been given to {community_user.name:,}!",
                message.MessageStatus.SUCCESS,
            )
        )


class TasksCog(cmds.GroupCog, group_name="tasks"):
    def __init__(self, bot: cmds.Bot) -> None:
        self.bot = bot

    @acmds.command()
    @acmds.rename(yield_="yield")
    @command.adapt
    async def browse(
        self,
        ia: InteractionAdapter,
        filter: str | None = None,
        sort: str | None = None,
        yield_: Yield = Yield.DEFAULT,
        list: str | None = None,
    ) -> CoroutineType[None, None, t.Any]:
        return await _browse(ia, filter, sort, yield_, ..., False, list)

    @acmds.command()
    @acmds.rename(yield_="yield")
    @command.adapt
    async def browse_user(
        self,
        ia: InteractionAdapter,
        filter: str | None = None,
        sort: str | None = None,
        yield_: Yield = Yield.DEFAULT,
        user: dc.User | None = None,
        list: str | None = None,
    ) -> CoroutineType[None, None, t.Any]:
        return await _browse(ia, filter, sort, yield_, user, False, list)

    @acmds.command()
    @acmds.rename(yield_="yield")
    @command.adapt
    async def browse_missing(
        self,
        ia: InteractionAdapter,
        filter: str | None = None,
        sort: str | None = None,
        yield_: Yield = Yield.DEFAULT,
        user: dc.User | None = None,
        list: str | None = None,
    ) -> CoroutineType[None, None, t.Any]:
        return await _browse(ia, filter, sort, yield_, user, True, list)
