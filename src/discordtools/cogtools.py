from discord.ext import commands

class BetterCogGroup(commands.GroupCog):
    def __init__(self, name: str) -> None:
        self.set_name(name)

    def set_name(self, name: str) -> None:
        if self.__cog_app_commands_group__ is not None:
            self.__cog_app_commands_group__.name = name