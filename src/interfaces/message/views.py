import asyncio
from collections.abc import Awaitable, Callable

import discord
from discord import ButtonStyle, ui


class DangerousConfirmView(ui.View):

    def __init__(
        self,
        *,
        user: discord.User | discord.Member,
        on_confirm: Callable[[], None],
        success_text: str,
        cancel_text: str,
        timeout: int,
    ) -> None:
        super().__init__(timeout=timeout)

        self._user = user
        self._on_confirm = on_confirm
        self._success_text = success_text
        self._cancel_text = cancel_text

        self._message: discord.WebhookMessage | None = None

        self.confirm.disabled = True
        self._enable_task = asyncio.create_task(self._enable_confirm())

    async def _enable_confirm(self) -> None:
        try:
            await asyncio.sleep(5)

            if self.is_finished() or self._message is None:
                return

            self.confirm.disabled = False
            await self._message.edit(view=self)

        except asyncio.CancelledError:
            pass

    async def on_timeout(self) -> None:
        self._enable_task.cancel()

        if self._message is not None:
            for child in self.children:
                if isinstance(child, ui.Button):
                    child.disabled = True

            await self._message.edit(view=self)

        self.stop()

    @ui.button(
        emoji="✅",
        style=ButtonStyle.danger,
        disabled=True,
    )
    async def confirm(
        self,
        interaction: discord.Interaction,
        _: ui.Button,
    ) -> None:
        if self._user.id != interaction.user.id:
            return

        self._enable_task.cancel()
        self.stop()

        self._on_confirm()

        if self._message is not None:
            await self._message.edit(
                content=self._success_text,
                view=None,
            )

    @ui.button(
        emoji="✖️",
        style=ButtonStyle.primary,
    )
    async def cancel(
        self,
        interaction: discord.Interaction,
        _: ui.Button,
    ) -> None:
        if self._user.id != interaction.user.id:
            return

        self._enable_task.cancel()
        self.stop()

        await interaction.response.edit_message(
            content=self._cancel_text,
            view=None,
        )
