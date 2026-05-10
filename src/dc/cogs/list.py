import typing as t
from collections import defaultdict
from types import CoroutineType

import discord.app_commands as acmds
import discord.ext.commands as cmds

from _adapters.interaction import _InteractionAdapter
from dc_utils import command, confirm, group, layouts, message, predicate, shortcuts
from structures.attribute import ALL_ATTRIBUTE_TYPES, AnyAttributeT
from structures.list import List
from structures.task import Task
from utils import itertools2
from domain.enum.rank import CommunityRank

_ListRow = command.row_type_factory[
    str,
    tuple[str, ...],
    tuple[str, ...],
    tuple[str, ...],
    str,
    str,
](
    "Name",
    "Static Attribute",
    "Task Attribute",
    "User Attribute",
    "Task Count",
    "Is Default Selected List",
)


class ListCog(cmds.GroupCog, group_name="list"):
    def __init__(self, bot: cmds.Bot) -> None:
        self.bot = bot

    @acmds.command()
    @command.adapt()
    async def info(
        self, ia: _InteractionAdapter, list: str | None = None
    ) -> CoroutineType[t.Any, t.Any, t.Any]:
        lst = shortcuts.get_specified_or_ia_user_selected_or_default_list(ia, list)._o

        attr_names: tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]] = tuple(tuple(attr.name for attr in attrs) for attrs in lst.get_attributes_grouped(ia._c))  # type: ignore

        return await command.info(
            ia,
            lst,
            _ListRow(
                lst.name,
                *attr_names,
                str(len(lst.get_tasks(ia._c))),
                (
                    "Yes"
                    if lst == lst.community.get_default_selected_list(ia._c)
                    else "No"
                ),
            ),
        )

    @acmds.command()
    @acmds.check(predicate.rank_required(CommunityRank.ADMINISTRATOR))
    @command.adapt()
    async def create(
        self, ia: _InteractionAdapter, name: str
    ) -> CoroutineType[t.Any, t.Any, t.Any]:
        community = shortcuts.get_current_community(ia)

        new_list = community.create_list(name)

        return ia.dc.followup.send(
            message.layout(
                "List Created",
                t"The list {new_list.name:,} has successfully been created!",
                message.MessageStatus.SUCCESS,
            )
        )

    @acmds.command()
    @acmds.check(predicate.rank_required(CommunityRank.ADMINISTRATOR))
    @command.adapt()
    async def nuke(
        self, ia: _InteractionAdapter, list: str
    ) -> CoroutineType[t.Any, t.Any, t.Any]:
        list_o = shortcuts.get_current_community(ia).get_list(list)._o

        return await confirm.confirm_nuke(
            ia, list_o, lambda: list_o.community.delete_list(ia._c, list_o.id)
        )

    list_edit_group = group.create_edit_group(CommunityRank.ADMINISTRATOR)

    @list_edit_group.command(name="name")
    @command.adapt()
    async def edit_name(
        self, ia: _InteractionAdapter, list: str, new_name: str
    ) -> CoroutineType[t.Any, t.Any, t.Any]:
        community = shortcuts.get_current_community(ia)

        lst, new_name = community.rename_list(list, new_name)

        return ia.dc.followup.send(layouts.structure_name_edited(lst, new_name))


class ListsCog(cmds.GroupCog, group_name="lists"):
    @acmds.command()
    @command.adapt()
    async def browse(
        self, ia: _InteractionAdapter
    ) -> CoroutineType[t.Any, t.Any, t.Any]:
        community = shortcuts.get_current_community(ia)
        lists = community.get_lists()

        attr_type_to_attrs: dict[int, defaultdict[int, list[AnyAttributeT]]] = {
            lst.id: itertools2.groupby_unsorted(
                lst._o.get_attributes(lst._c), lambda attr: type(attr).type_id
            )
            for lst in lists
        }
        dsl = community.get_default_selected_list(None)
        lst_to_task = community._o.get_tasks_by_list(ia._c)

        list_to_attr_strings: dict[int, tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]] = {lst.id: tuple(tuple(attr.name for attr in attr_type_to_attrs[lst.id][attr_type.type_id]) for attr_type in ALL_ATTRIBUTE_TYPES) for lst in lists}  # type: ignore

        return await command.browse(
            ia,
            List,
            tuple(
                _ListRow(
                    lst.name,
                    *list_to_attr_strings[lst.id],
                    str(len(lst_to_task.get(lst._o, []))),
                    "Yes" if dsl == lst else "No",
                )
                for lst in lists
            ),
        )
