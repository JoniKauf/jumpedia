import discord as dc
from discord import app_commands
from domain.value_objects.s import StrStore
from interface.base import BaseInterface
from service.list import ListService
from service.user import UserService


class ListInterface(BaseInterface):
    def __init__(self, user_service: UserService, list_service: ListService) -> None:
        super().__init__(user_service)
        self.list_service = list_service