import typing as t
from collections import defaultdict
from string.templatelib import Template
from types import CoroutineType
from typing import Any

import discord.app_commands as acmds
import discord.ext.commands as cmds

from adapting._user import UserAdapter
from adapting.interaction import InteractionAdapter
from dc_utils import command, layouts, message, modal, predicate, shortcuts
from dc_utils.rank import CommunityRank
from structures.attribute import ALL_ATTRIBUTE_TYPES, AnyAttributeT
from structures.list import List
from structures.task import Task
from utils import itertools2


class ListCog(cmds.GroupCog, group_name="list"):
    def __init__(self, bot: cmds.Bot) -> None:
        self.bot = bot

    @acmds.command(description="Show information about a list.")
    @command.adapt
    async def info(
        self, ia: InteractionAdapter, list: str | None = None
    ) -> CoroutineType[None, None, t.Any]:
        list_obj = shortcuts.get_specified_or_selected_or_default_list(ia, None, list)

        info: list[tuple[str, Any]] = [("Name", list_obj.name)]

        attributes = list_obj.get_all_attributes()

        info.append(("Total Attribute Count", sum(len(type) for type in attributes)))

        for i, type in enumerate(attributes):
            info.append(
                (f"{ALL_ATTRIBUTE_TYPES[i].type_name.title()} Count", len(type))
            )

        info.append(("Task Count", len(list_obj.get_tasks())))

        return ia.dc.response.send_message(
            message.layout(
                "List Info",
                Template("\n".join(f"**{k}:** {v}" for k, v in info)),
                message.MessageStatus.INFO,
            )
        )

    @acmds.command(description="Create a new list.")
    @acmds.check(predicate.rank_required(CommunityRank.ADMINISTRATOR))
    @command.adapt
    async def create(
        self, ia: InteractionAdapter, list: str
    ) -> CoroutineType[None, None, t.Any]:
        community = shortcuts.get_current_community(ia)

        new_list = community.create_list(list)

        return ia.dc.response.send_message(
            message.layout(
                "List Created",
                t"The list {new_list.name:,} has successfully been created!",
                message.MessageStatus.SUCCESS,
            )
        )

    @acmds.command()
    @acmds.check(predicate.rank_required(CommunityRank.ADMINISTRATOR))
    @command.adapt
    async def rename(
        self, ia: InteractionAdapter, list: str, new_name: str
    ) -> CoroutineType[None, None, t.Any]:
        community = shortcuts.get_current_community(ia)

        old_name, new_name = community.rename_list(list, new_name)

        return ia.dc.response.send_message(
            layouts.success(
                "List Renamed",
                t"The list {old_name:,} has successfully been renamed to {new_name:,}!",
            )
        )

    @acmds.command(description="Delete an existing list.")
    @acmds.check(predicate.rank_required(CommunityRank.ADMINISTRATOR))
    @command.adapt
    async def nuke(
        self, ia: InteractionAdapter, list: str
    ) -> CoroutineType[None, None, t.Any]:
        list_s = shortcuts.get_current_community(ia).get_list(list)._o

        return modal.delete_structure_confirmation(
            ia.dc,
            List,
            list_s.name,
            lambda _: list_s.community.delete_list(ia._c, list_s.id),
        )


class ListsCog(cmds.GroupCog, group_name="lists"):
    @acmds.command(description="Browse all lists of the community.")
    @command.adapt
    async def browse(self, ia: InteractionAdapter) -> CoroutineType[None, None, t.Any]:
        await ia.dc.response.defer()

        community = shortcuts.get_current_community(ia)
        lists = community.get_lists()

        attr_type_to_attrs: dict[int, defaultdict[int, list[AnyAttributeT]]] = {
            lst.id: itertools2.groupby_unsorted(
                lst._o.get_attributes(lst._c), lambda attr: type(attr).type_id
            )
            for lst in lists
        }
        dsl = community.get_default_selected_list()

        data: dict[str, tuple[str | tuple[str, ...], ...]] = {
            "Name": tuple(lst.name for lst in lists),
            **{
                attr_type.type_name_plural.title(): tuple(
                    tuple(
                        attr.name
                        for attr in attr_type_to_attrs[lst.id].get(
                            attr_type.type_id, ()
                        )
                    )
                    for lst in lists
                )
                for attr_type in ALL_ATTRIBUTE_TYPES
            },
            Task.type_name_plural.title(): tuple(
                str(len(lst.get_tasks())) for lst in lists
            ),
            "Is Default Selected List": tuple(
                "Yes" if dsl == lst else "No" for lst in lists
            ),
        }

        return ia.dc.followup.send(
            await layouts.browse(List, tuple(zip(*data.values())), tuple(data)),
            suppress_embeds=True,
        )
