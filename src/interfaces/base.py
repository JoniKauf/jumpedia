import discord
from discord.ext import commands
import typing as t
from domain.enums.rank import ServerRank
from services.user import UserService


class InterfaceMeta(commands.CogMeta):
    def __new__(
        mcls,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, t.Any],
        *,
        group_name: str,
        **kwargs: t.Any,
    ):
        return super().__new__(mcls, name, bases, namespace, group_name, **kwargs)


class BaseInterface(commands.GroupCog, metaclass=InterfaceMeta, group_name="base"):
    pass