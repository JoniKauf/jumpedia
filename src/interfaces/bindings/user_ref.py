import typing as t

import discord

from domain.sentinels.default import DEFAULT
from domain.typing.common import ID
from domain.typing.user import UserID
from domain.value_objects.user import UserNameStr
from services.dtos.user import UserRef


@t.overload
def user_ref(user: discord.User) -> UserRef:
    pass


@t.overload
def user_ref(user: None) -> DEFAULT:
    pass


def user_ref(user: discord.User | None) -> UserRef | DEFAULT:
    return (
        DEFAULT
        if user is None
        else UserRef(UserID(ID(user.id)), UserNameStr(user.name))
    )
