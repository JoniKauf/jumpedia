import asyncio
import typing as t

import discord as dc
from discord import ui

from structures import BaseStructure

from ..utils_ import messaging


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
            messaging.layout(
                "Awaiting Confirmation",
                "Please fill out the modal that should be appearing on your screen to confirm!",
                messaging.MessageStatus.INFO,
            ),
            ephemeral=True,
        )

    async def dispose(self):
        await asyncio.sleep(self.virtual_timeout)

        self.stop()

    async def on_submit(self, ia: dc.Interaction) -> None:
        await self.after_submit(ia, self.predicate(self.text_input.value))


async def delete_structure_confirmation(
    interaction: dc.Interaction,
    structure: BaseStructure,
    delete: t.Callable[[dc.Interaction], None],
):
    async def after_submit(interaction: dc.Interaction, success: bool) -> None:
        if success:
            delete(interaction)

            await interaction.response.send_message(
                messaging.layout(
                    f"{structure.__class__.type_name.title()} Deleted",
                    f"The specifed {structure.__class__.type_name} has successfully been deleted!",
                    messaging.MessageStatus.SUCCESS,
                )
            )
        else:
            await interaction.response.send_message(
                messaging.layout(
                    f"{structure.__class__.type_name.title()} Deletion Aborted",
                    f"The {structure.__class__.type_name} has **not** been deleted because the name entered is not correct!",
                    messaging.MessageStatus.WARNING,
                )
            )

    await interaction.response.send_modal(
        ConfirmByEnteringModal(
            interaction,
            f"Confirm {structure.__class__.type_name.title()} Deletion",
            f"Re-Enter the {structure.__class__.type_name}'s name to confirm:",
            lambda s: s == structure.name,
            after_submit,
        )
    )
