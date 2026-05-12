

import functools

import discord
from discord.ext import commands
import typing as t
import types as ts

from sqlalchemy.orm import Session

import db.session
from domain.enums.rank import AnyRankT, JumpediaRank
from domain.value_objects import s

if t.TYPE_CHECKING:
    from interface.base import BaseInterface

def adapt[T: BaseInterface, **P](rank_required: AnyRankT):
    def decorator(
        func: t.Callable[
            t.Concatenate[T, Session, discord.Interaction, P],
            t.Awaitable[None],
        ]
    ) -> t.Callable[
        t.Concatenate[T, discord.Interaction, P],
        t.Awaitable[None],
    ]:
        @functools.wraps(func)
        async def wrapper(
            self: T,
            interaction: discord.Interaction,
            *args: P.args,
            **kwargs: P.kwargs,
        ) -> None:
            with db.session.get_session() as session:
                try:
                    self.user_service.get_or_create_user(
                        user_id=interaction.user.id,
                        name=s.StrStore(interaction.user.global_name or interaction.user.name),
                        rank=JumpediaRank.DEFAULT
                    )

                    self.user_service.get_or_create_community_user()

                    # --- call actual handler ---
                    await func(self, session, interaction, *args, **kwargs)

                except PermissionError as e:
                    await interaction.response.send_message(str(e), ephemeral=True)

                except Exception:
                    # optional: logging here
                    await interaction.response.send_message(
                        "Internal error", ephemeral=True
                    )
                    raise

        return wrapper

    return decorator