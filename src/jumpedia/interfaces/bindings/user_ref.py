import typing as t

import discord
from discord.ext import commands

from jumpedia.domain.enums.concept import Concept
from jumpedia.domain.errors.business import NotFoundByName
from jumpedia.domain.sentinels.default import DEFAULT
from jumpedia.domain.typing.common import ID
from jumpedia.domain.typing.user import UserID
from jumpedia.domain.value_objects.string import Str
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


async def user_from_mention(bot: commands.Bot, mention: str) -> discord.User:
    """Get the user of a mention like `<@123>` or of a plain Discord ID."""

    user_id = mention.strip("<@!>")

    if not user_id.isdecimal():
        raise NotFoundByName(Concept.USER, Str(mention))

    try:
        return bot.get_user(int(user_id)) or await bot.fetch_user(int(user_id))
    except discord.HTTPException as e:
        # Discord answers an unknown ID with 404 and one that is too big with 400.
        if e.status not in (400, 404):
            raise

        raise NotFoundByName(Concept.USER, Str(mention))
