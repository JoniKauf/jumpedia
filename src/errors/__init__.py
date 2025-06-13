import textwrap
import traceback
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


class FeedbackError(BaseUserReturnableError):
    """Its string representation shows a customizable, user-friendly error message."""

    def __init__(self, header: str, core: str, *, additional: str | None = None, related_documentation: Sequence[tuple[str, str]] = (), paragraphs: Sequence[str] = (), msg_kwargs: Mapping[str, Any] | None = None):
        self.header = header
        self.core = core
        self.additional = additional
        self.related_documentation = related_documentation
        self.paragraphs = paragraphs

        super().__init__(**(msg_kwargs or {}))
    

    def __str__(self) -> str:
        paragraphs: list[str] = list(self.paragraphs)

        if self.related_documentation:
            paragraphs.append(
                "### Related Documentation\n" 
                + 
                '\n'.join(
                    f"[{name}]({link})" 
                    for name, link in 
                    self.related_documentation
                )
            )

        return messaging.layout(
            header=self.header,
            core=self.core,
            message_status=messaging.MessageStatus.FAILED,
            paragraphs=paragraphs
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