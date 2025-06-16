from typing import Any, Mapping, Sequence
from discord.app_commands.errors import CheckFailure

from discordtools import messaging

class ImpossibleError(RuntimeError):
    """
    An error that is thrown whenever a part in the code is reached that should
    not have been possible to be reached.
    """
    ...

class BaseUserReturnableError(RuntimeError, CheckFailure):
    """
    Marks an exception whose string representation can be returned to the user on Discord. 
    """

    def __init__(self, *args: Any, **msg_kwargs: Any) -> None:
        if self.__class__ == BaseUserReturnableError:
            raise RuntimeError(f"{self.__class__.__name__} is a base class and must be inherited")
        
        self.msg_kwargs = msg_kwargs
        super().__init__(*args)
    
class SetupError(RuntimeError):
    """
    Raised when the setup process doesn't fully work.
    Critical, so it stops the process.
    """

    def __init__(self, *args):
        super().__init__(*args) 
    
    def __exception__(self, exc_type, exc_value, traceback):
        exit()