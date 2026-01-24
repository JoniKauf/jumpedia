import enum
import typing as t
from collections import namedtuple
from types import CoroutineType, EllipsisType

import discord as dc
import discord.app_commands as acmds
import discord.ext.commands as cmds

from adapting import parsing
from adapting.interaction import InteractionAdapter
from dc_utils import command, layouts, message, predicate, shortcuts
from dc_utils.rank import CommunityRank
from structures.attribute import AnyAttributeT, StaticAttribute
from structures.list import Kind
from structures.task import Task
from structures.task.attribute_value_mapping import (
    AttributeValueMapping,
    UserAttributeValueMapping,
)
from utils.text import NormStr, RealStr


async def _info(
    ia: InteractionAdapter,
    task: str,
    user: dc.User | None | EllipsisType,
    list: str | None,
) -> CoroutineType[t.Any, t.Any, t.Any]:
    list_obj = shortcuts.get_specified_or_ia_user_selected_or_default_list(ia, list)
    task_obj = list_obj.get_task(task)

    avm = task_obj.get_attribute_value_mapping(
        None
        if user is ...
        else shortcuts.get_or_create_specified_or_current_community_user(
            list_obj.community, user
        )
    )

    return await command.info(
        ia,
        task_obj._o,
        namedtuple("_TaskRow", [attr.name for attr in avm.combined])(
            *avm.combined.values()
        ),
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
) -> CoroutineType[t.Any, t.Any, t.Any]:
    finished_content: str = ""
    prev_content: str = ""

    def update_loading(s: str) -> str:
        nonlocal finished_content, prev_content

        if prev_content:
            finished_content += f"✅ {prev_content}\n"

        prev_content = s

        return finished_content + f"⚙️ {s}"

    list_obj = shortcuts.get_specified_or_ia_user_selected_or_default_list(ia, list)

    community_user = shortcuts.get_or_create_specified_or_current_community_user(
        list_obj.community, None if user is ... else user
    )

    msg = await ia.dc.followup.send(
        update_loading("Retrieving data..."), suppress_embeds=True, wait=True
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

    ATTRS_SORTED_YIELDED: t.Final[tuple[AnyAttributeT, ...]] = tuple(
        attr for attr in ATTRS_SORTED if attr in attribute_yield
    )

    _TaskRow = namedtuple("_TaskRow", [attr.norm_name for attr in ATTRS_SORTED_YIELDED])

    return await command.browse(
        ia,
        Task,
        rows=tuple(
            _TaskRow(
                *(
                    avm.combined.get(attr, ())  # type: ignore
                    for attr in ATTRS_SORTED_YIELDED
                )
            )
            for avm in avms
        ),
        before_send=lambda strings: msg.edit(
            content=update_loading(
                f"Sending text to GitHub Gist... ({sum(map(len, strings)):,} Bytes across {len(strings)} file{'s' if len(strings) > 1 else ''})"
            )
        ),
        edit_msg=msg,
    )


class TaskCog(cmds.GroupCog, group_name="task"):
    def __init__(self, bot: cmds.Bot) -> None:
        self.bot = bot

    @acmds.command()
    @command.adapt()
    async def info(
        self, ia: InteractionAdapter, task: str, list: str | None = None
    ) -> CoroutineType[t.Any, t.Any, t.Any]:
        return await _info(ia, task, ..., list)

    @acmds.command()
    @command.adapt(rank_to_specify_user=None)
    async def info_user(
        self,
        ia: InteractionAdapter,
        task: str,
        user: dc.User | None = None,
        list: str | None = None,
    ) -> CoroutineType[t.Any, t.Any, t.Any]:
        return await _info(ia, task, user, list)

    @acmds.command()
    @acmds.check(predicate.rank_required(CommunityRank.HELPER))
    @command.adapt()
    async def create(
        self,
        ia: InteractionAdapter,
        name: str,
        aliases: str | None = None,
        task_attribute_value_mapping: str | None = None,
        list: str | None = None,
    ) -> CoroutineType[t.Any, t.Any, t.Any]:
        list_obj = shortcuts.get_specified_or_ia_user_selected_or_default_list(ia, list)

        task = list_obj.create_task(name, aliases, task_attribute_value_mapping)

        return ia.dc.followup.send(
            message.layout(
                "Task Created",
                t"The task {task.name:,} has successfully been created!",
                message.MessageStatus.SUCCESS,
            )
        )

    task_edit_group = acmds.Group(name="edit", description="Edit task data.")

    @task_edit_group.command(name="name")
    @acmds.check(predicate.rank_required(CommunityRank.MODERATOR))
    @command.adapt()
    async def edit_name(
        self, ia: InteractionAdapter, task: str, new_name: str, list: str | None = None
    ) -> CoroutineType[t.Any, t.Any, t.Any]:
        list_obj = shortcuts.get_specified_or_ia_user_selected_or_default_list(ia, list)

        old_task = list_obj.edit_task_name(task, new_name)

        return ia.dc.followup.send(
            layouts.success(
                "Task Name Edited",
                t"The name of the "
                + old_task.mention()
                + t" has successfully been changed to {RealStr(new_name):,}!",
            )
        )

    @task_edit_group.command(name="aliases")
    @acmds.check(predicate.rank_required(CommunityRank.MODERATOR))
    @command.adapt()
    async def edit_aliases(
        self,
        ia: InteractionAdapter,
        name: str,
        new_aliases: str,
        list: str | None = None,
    ) -> CoroutineType[t.Any, t.Any, t.Any]:
        list_obj = shortcuts.get_specified_or_ia_user_selected_or_default_list(ia, list)

        old_task, real_aliases = list_obj.edit_task_aliases(name, new_aliases)

        return ia.dc.followup.send(
            layouts.success(
                "Task Aliases Edited",
                t"The aliases of the "
                + old_task.mention()
                + t" have successfully been changed to {real_aliases:,}!",
            )
        )

    @task_edit_group.command(name="task_attribute_value_mapping")
    @acmds.check(predicate.rank_required(CommunityRank.MODERATOR))
    @command.adapt()
    async def edit_task_attribute_value_mapping(
        self,
        ia: InteractionAdapter,
        name: str,
        new_attribute_value_mapping: str | None = None,
        list: str | None = None,
    ) -> CoroutineType[t.Any, t.Any, t.Any]:
        list_obj = shortcuts.get_specified_or_ia_user_selected_or_default_list(ia, list)

        old_task = list_obj.edit_task_attribute_value_mapping(
            name, new_attribute_value_mapping
        )

        return ia.dc.followup.send(
            layouts.success(
                "Task Attribute Value Mapping Edited",
                t"The (task) attribute value mapping of the "
                + old_task.mention()
                + t" has successfully been changed!",
                additional=t"Use the {TaskCog.info.qualified_name:,} command to see the new mapping.",
            )
        )

    @acmds.command()
    @acmds.check(predicate.rank_required(CommunityRank.MODERATOR))
    @command.adapt()
    async def nuke(
        self, ia: InteractionAdapter, task: str, list: str | None = None
    ) -> CoroutineType[t.Any, t.Any, t.Any]:
        list_obj = shortcuts.get_specified_or_ia_user_selected_or_default_list(ia, list)

        list_obj.delete_task(task)

        return ia.dc.followup.send(
            message.layout(
                "Task Delete",
                t"The task {task:,} has successfully been deleted!",
                message.MessageStatus.SUCCESS,
            )
        )

    @acmds.command()
    @command.adapt()
    async def give(
        self,
        ia: InteractionAdapter,
        task: str,
        user_attribute_value_mapping: str | None = None,
        user: dc.User | None = None,
        list: str | None = None,
    ) -> CoroutineType[t.Any, t.Any, t.Any]:
        community_user = shortcuts.get_or_create_specified_or_current_community_user(
            ia, user
        )
        list_obj = shortcuts.get_specified_or_ia_user_selected_or_default_list(
            community_user.community, list
        )

        task_obj = list_obj.give_task_to_user(
            task, community_user, user_attribute_value_mapping
        )

        return ia.dc.followup.send(
            layouts.info(
                "Task Given",
                t"The task {task_obj.name:,} has successfully been given to {community_user.name:,}!",
            )
        )

    @acmds.command()
    @command.adapt()
    async def take(
        self,
        ia: InteractionAdapter,
        task: str,
        user: dc.User | None = None,
        list: str | None = None,
    ) -> CoroutineType[t.Any, t.Any, t.Any]:
        list_obj = shortcuts.get_specified_or_ia_user_selected_or_default_list(ia, list)
        community_user = shortcuts.get_or_create_specified_or_current_community_user(
            list_obj.community, user
        )

        task_obj = list_obj.remove_task_from_user(task, community_user)

        return ia.dc.followup.send(
            layouts.success(
                "Task Taken",
                t"The task "
                + task_obj.mention()
                + t" has successfully been taken from {community_user:,}!",
            )
        )


class TasksCog(cmds.GroupCog, group_name="tasks"):
    def __init__(self, bot: cmds.Bot) -> None:
        self.bot = bot

    @acmds.command()
    @acmds.rename(yield_="yield")
    @command.adapt()
    async def browse(
        self,
        ia: InteractionAdapter,
        filter: str | None = None,
        sort: str | None = None,
        yield_: Yield = Yield.DEFAULT,
        list: str | None = None,
    ) -> CoroutineType[t.Any, t.Any, t.Any]:
        return await _browse(ia, filter, sort, yield_, ..., False, list)

    @acmds.command()
    @acmds.rename(yield_="yield")
    @command.adapt(rank_to_specify_user=None)
    async def browse_user(
        self,
        ia: InteractionAdapter,
        filter: str | None = None,
        sort: str | None = None,
        yield_: Yield = Yield.DEFAULT,
        user: dc.User | None = None,
        list: str | None = None,
    ) -> CoroutineType[t.Any, t.Any, t.Any]:
        return await _browse(ia, filter, sort, yield_, user, False, list)

    @acmds.command()
    @acmds.rename(yield_="yield")
    @command.adapt(rank_to_specify_user=None)
    async def browse_missing(
        self,
        ia: InteractionAdapter,
        filter: str | None = None,
        sort: str | None = None,
        yield_: Yield = Yield.DEFAULT,
        user: dc.User | None = None,
        list: str | None = None,
    ) -> CoroutineType[t.Any, t.Any, t.Any]:
        return await _browse(ia, filter, sort, yield_, user, True, list)
