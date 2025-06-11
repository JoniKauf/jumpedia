import textwrap
from typing import Any, Sequence
from discord.app_commands.errors import CheckFailure

from discordtools import messaging

class ImpossibleError(RuntimeError):
    """
    An error that is thrown whenever a part in the code is reached that should
    not have been reached.
    """
    ...

class UserReturnableError(RuntimeError, CheckFailure):
    """
    Marks an exception whose string representation can be returned to the user on Discord. 
    """

    def __init__(self, *args: Any, **msg_kwargs: Any) -> None:
        self.msg_kwargs = msg_kwargs
        super().__init__(*args)


class BaseFeedbackError(UserReturnableError):
    """Its string representation shows a customizable, user-friendly error message."""

    def __init__(self, *, header: str, body: str, docs: Sequence[str] = (), **msg_kwargs: Any):
        if self.__class__ == BaseFeedbackError:
            raise ImpossibleError("Must be subclass of feedbackerror")
        
        self.header = header
        self.body = body
        self.docs = docs

        super().__init__(**msg_kwargs)
    

    def __str__(self) -> str:
        return messaging.layout(
            header=self.header,
            body=self.body,
            message_status=messaging.MessageStatus.FAILED,
            more=self.docs
        )
    

class SetupError(RuntimeError):
    """
    Raised when the setup process doesn't fully work.
    Critical, so it stops the process.
    """

    def __init__(self, *args):
        super().__init__(*args) 
    
    def __exception__(self, exc_type, exc_value, traceback):
        exit()