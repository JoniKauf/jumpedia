import typing as t

import discord

from jumpedia.domain.sentinels.default import DEFAULT
from jumpedia.domain.typing.common import ID
from jumpedia.domain.typing.user import UserID
from jumpedia.domain.value_objects.user import UserNameStr
from jumpedia.services.dtos.user import UserRef


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
