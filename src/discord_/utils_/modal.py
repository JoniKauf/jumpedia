import asyncio
import typing as t

import discord as dc
from discord import ui

from structures import BaseStructure

from . import message


class ConfirmByEnteringModal(ui.Modal):
    def __init__(
        self,
        interaction: dc.Interaction,
        title: str,
        label: str,
        predicate: t.Callable[[str], bool],
        after_submit: t.Callable[
            [dc.Interaction, bool], t.Coroutine[t.Any, t.Any, None]
        ],
        timeout: float = 180,
    ) -> None:
        super().__init__(title=title, timeout=timeout)

        self.predicate = predicate
        self.after_submit = after_submit

        self.text_input = ui.TextInput(label=label, style=dc.TextStyle.short)
        self.text_input.placeholder = (
            "This action is irreversable and cannot be undone!"
        )
        self.add_item(self.text_input)

        self.virtual_timeout = timeout

        asyncio.create_task(self.info_message(interaction))
        asyncio.create_task(self.dispose())

    async def info_message(self, interaction: dc.Interaction) -> None:
        await interaction.followup.send(
            message.layout(
                "Awaiting Confirmation",
                t"Please fill out the modal that should be appearing on your screen to confirm!",
                message.MessageStatus.INFO,
            ),
            ephemeral=True,
        )

    async def dispose(self):
        await asyncio.sleep(self.virtual_timeout)

        self.stop()

    async def on_submit(self, ia: dc.Interaction) -> None:
        await self.after_submit(ia, self.predicate(self.text_input.value))
        self.stop()


async def delete_structure_confirmation(
    interaction: dc.Interaction,
    structure_type: type[BaseStructure],
    structure_name: str,
    delete: t.Callable[[dc.Interaction], t.Any],
):
    async def after_submit(interaction: dc.Interaction, success: bool) -> None:
        if success:
            delete(interaction)

            await interaction.response.send_message(
                message.layout(
                    f"{structure_type.type_name.title()} Deleted",
                    t"The specifed {structure_type.type_name} has successfully been deleted!",
                    message.MessageStatus.SUCCESS,
                )
            )
        else:
            await interaction.response.send_message(
                message.layout(
                    f"{structure_type.type_name.title()} Deletion Aborted",
                    t"The {structure_type.type_name} has **not** been deleted because the name entered is not correct!",
                    message.MessageStatus.WARNING,
                )
            )

    await interaction.response.send_modal(
        ConfirmByEnteringModal(
            interaction,
            f"Confirm {structure_type.type_name.title()} Deletion",
            f"Enter the {structure_type.type_name}'s name to confirm:",
            lambda s: s == structure_name,
            after_submit,
        )
    )
