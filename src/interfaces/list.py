from discord import app_commands
import discord
from core.container import CommunityService
from domain.enums.rank import JumpediaRank
from domain.value_objects.strings import StrStore
from interfaces.base import BaseInterface
from interfaces.decorators.context import CommandContext, with_context
from services.list import ListService
from services.user import UserService
from sqlalchemy.orm import Session

class ListInterface(BaseInterface, group_name="list"):
    def __init__(self, user_service: UserService, community_service: CommunityService, list_service: ListService) -> None:
        super().__init__(user_service, community_service)
        self.list_service = list_service


    @app_commands.command()
    @with_context()
    async def info(self, context: CommandContext, name: str) -> None:
        info = ListService(context.session).info(context.member.id, StrStore(name))