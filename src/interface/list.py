import discord as dc
from domain.value_objects.s import StrStore
from interface.base import BaseInterface
from service.list import ListService


class List(BaseInterface[ListService]):
    def create_list(self, interaction: dc.Interaction, name: str) -> None:
        try:

        except Exception as e:
            ctx.send(f"Error: {e}")

    def rename_list(self, ctx) -> None:
        try:
            list_id: int = int(ctx.args["list_id"])
            name_input: str = ctx.args["name"]

            new_name = StrStore(name_input)

            self.service.rename_list(
                list_id=list_id,
                new_name=new_name,
            )

            ctx.send("List renamed.")

        except Exception as e:
            ctx.send(f"Error: {e}")