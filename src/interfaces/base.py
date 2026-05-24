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
    def __init__(self, user_service: UserService) -> None:
        super().__init__()
        self.user_service = user_service

    @staticmethod
    def get_server_rank(member: discord.Member) -> ServerRank:
        owner = member.guild.owner

        if owner is not None and member.id == owner.id:
            return ServerRank.OWNER

        if member.guild_permissions.administrator:
            return ServerRank.ADMINISTRATOR

        return ServerRank.USER
