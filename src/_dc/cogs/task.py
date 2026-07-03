import enum
import typing as t
from collections import namedtuple
from types import CoroutineType, EllipsisType

import discord as dc
import discord.app_commands as acmds
import discord.ext.commands as cmds
from _adapters import BaseStructureAdapter
from _adapters.interaction import _InteractionAdapter
from structures.attribute import AnyAttributeT, StaticAttribute, UserAttribute
from structures.list import Kind
from structures.task import Task
from structures.task.attribute_value_mapping import (
    AttributeValueMapping,
    UserAttributeValueMapping,
)

from _dc_utils import command, group, layouts, message, parsing, predicate, shortcuts
from domain.enum.rank import CommunityRank
from utils.text import NormStr, RealStr


async def _info(
    ia: _InteractionAdapter,
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
        command.row_type_factory(*(attr.name for attr in avm.combined))(
            *avm.combined.values()
        ),
    )


class Yield(enum.Enum):
    DEFAULT = enum.auto()
    ONLY_NAME = enum.auto()
    ALL = enum.auto()


async def _browse(
    ia: _InteractionAdapter,
    filter: str | None,
    sort: str | None,
    yield_: Yield,
    user: dc.User | None | EllipsisType,
    given: bool,
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

        if given:
            task_ids_to_fetch = user_task_ids
        else:
            task_ids_to_fetch = tuple(
                set(task.id for task in list_obj.get_tasks()).difference(user_task_ids)
            )

        # Don't include user attribute values when missing, because those don't have any values, because well they are missing
        avms, attrs, ATTRIBUTE_TYPES_TO_HANDLE = (
            list_obj._o.get_attribute_value_mappings(
                ia._c, community_user._o.id if given else None, task_ids_to_fetch
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

        if user is not ...:
            attribute_yield |= {
                attr for attr in ATTRS_SORTED if isinstance(attr, UserAttribute)
            }

    elif yield_ is Yield.ONLY_NAME:
        attribute_yield = {NAME_ATTR}
    elif yield_ is Yield.ALL:
        attribute_yield = set(ATTRS_SORTED)
    else:
        t.assert_never(yield_)

    ATTRS_SORTED_YIELDED: t.Final[tuple[AnyAttributeT, ...]] = tuple(
        attr for attr in ATTRS_SORTED if attr in attribute_yield
    )

    _TaskRow = command.row_type_factory(*(attr.name for attr in ATTRS_SORTED_YIELDED))

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
        self, ia: _InteractionAdapter, task: str, list: str | None = None
    ) -> CoroutineType[t.Any, t.Any, t.Any]:
        return await _info(ia, task, ..., list)

    @acmds.command()
    @command.adapt(rank_to_specify_user=None)
    async def info_user(
        self,
        ia: _InteractionAdapter,
        task: str,
        user: dc.User | None = None,
        list: str | None = None,
    ) -> CoroutineType[t.Any, t.Any, t.Any]:
        return await _info(ia, task, user, list)

    @acmds.command()
    @command.adapt()
    async def give(
        self,
        ia: _InteractionAdapter,
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
            layouts.success(
                "Task Given",
                t"The "
                + task_obj.mention()
                + t" has been given to the "
                + BaseStructureAdapter.mention(community_user)
                + t" successfully!",
            )
        )

    @acmds.command()
    @command.adapt()
    async def take(
        self,
        ia: _InteractionAdapter,
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
                + t" has been taken from the "
                + community_user.mention()
                + t" successfully!",
            )
        )

    # --- Privileged ---

    @acmds.command()
    @acmds.check(predicate.rank_required(CommunityRank.HELPER))
    @command.adapt()
    async def create(
        self,
        ia: _InteractionAdapter,
        list: str,
        name: str,
        aliases: str | None = None,
        task_field_mapping: str | None = None,
    ) -> CoroutineType[t.Any, t.Any, t.Any]:
        list_obj = shortcuts.get_specified_or_ia_user_selected_or_default_list(ia, list)

        task_obj = list_obj.create_task(name, aliases, task_field_mapping)

        return ia.dc.followup.send(layouts.structure_created(task_obj._o))

    @acmds.command()
    @acmds.check(predicate.rank_required(CommunityRank.MODERATOR))
    @command.adapt()
    async def nuke(
        self, ia: _InteractionAdapter, list: str, task: str
    ) -> CoroutineType[t.Any, t.Any, t.Any]:
        list_obj = shortcuts.get_specified_or_ia_user_selected_or_default_list(ia, list)

        nuked_task = list_obj.delete_task(task)

        return ia.dc.followup.send(layouts.structure_nuked(nuked_task._o))

    task_edit_group = group.create_edit_group(CommunityRank.MODERATOR)

    @task_edit_group.command(name="name")
    @command.adapt()
    async def edit_name(
        self, ia: _InteractionAdapter, list: str, task: str, new_name: str
    ) -> CoroutineType[t.Any, t.Any, t.Any]:
        list_obj = shortcuts.get_specified_or_ia_user_selected_or_default_list(ia, list)

        old_task, new_name = list_obj.edit_task_name(task, new_name)

        return ia.dc.followup.send(layouts.structure_name_edited(old_task._o, new_name))

    @task_edit_group.command(name="aliases")
    @command.adapt()
    async def edit_aliases(
        self,
        ia: _InteractionAdapter,
        list: str,
        task: str,
        new_aliases: str,
    ) -> CoroutineType[t.Any, t.Any, t.Any]:
        list_obj = shortcuts.get_specified_or_ia_user_selected_or_default_list(ia, list)

        old_task, slot_aliases = list_obj.edit_task_aliases(task, new_aliases)

        return ia.dc.followup.send(
            layouts.structure_aliases_edited(old_task._o, slot_aliases)
        )

    @task_edit_group.command(name="attribute_value_mapping")
    @command.adapt()
    async def edit_attribute_value_mapping(
        self,
        ia: _InteractionAdapter,
        list: str,
        task: str,
        new_attribute_value_mapping: str | None = None,
    ) -> CoroutineType[t.Any, t.Any, t.Any]:
        list_obj = shortcuts.get_specified_or_ia_user_selected_or_default_list(ia, list)

        old_task = list_obj.edit_task_attribute_value_mapping(
            task, new_attribute_value_mapping
        )

        return ia.dc.followup.send(
            layouts.success(
                "Task Attribute Value Mapping Edited",
                t"The (task) attribute value mapping of the "
                + old_task.mention()
                + t" has been changed successfully!",
                additional=t"Use the {TaskCog.info.qualified_name:,} command to see the new mapping.",
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
        ia: _InteractionAdapter,
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
        ia: _InteractionAdapter,
        filter: str | None = None,
        sort: str | None = None,
        yield_: Yield = Yield.DEFAULT,
        given: bool = True,
        user: dc.User | None = None,
        list: str | None = None,
    ) -> CoroutineType[t.Any, t.Any, t.Any]:
        return await _browse(ia, filter, sort, yield_, user, given, list)
