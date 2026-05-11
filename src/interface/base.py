from service.base import BaseService
from discord.ext.commands import GroupCog

class BaseInterface[T: BaseService](GroupCog):
    def __init__(self, service: T) -> None:
        self.service = service
    