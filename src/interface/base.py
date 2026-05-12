from service.base import BaseService
from discord.ext.commands import GroupCog

from service.user import UserService

class BaseInterface(GroupCog):
    def __init__(self, user_service: UserService) -> None:
        super().__init__()
        self.user_service = user_service