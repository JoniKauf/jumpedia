import textwrap
from typing import Optional, Sequence
import discordtools.messagetools as msgt
from numbers import Real


class ProgrammingError(RuntimeError):
    """
    An error that is thrown whenever a part in the code is reached that should
    not have been reached.
    """
    ...


class UserReturnableError(RuntimeError):
    """
    Marks an exception whose string representation can be returned to the user on Discord. 
    """

    def __init__(self, *args, **msg_kwargs) -> None:
        self.msg_kwargs = msg_kwargs
        super().__init__(*args)


class FeedbackError(UserReturnableError):
    """Its string representation shows a customizable, user-friendly error message."""

    def __init__(self, *, error: str, details: str, docs: Optional[Sequence[str]] = None, **msg_kwargs):
        if self.__class__ == FeedbackError:
            raise ProgrammingError()

        self.error = error
        self.details = details
        self.docs = docs

        

        super().__init__(**msg_kwargs)
    

    def __str__(self) -> str:
        parts = []

        parts.append(f"### {self.error}")
        parts.append(self.details)

        if self.docs:
            parts.append("### Documentation")
            
            for doc in self.docs:
                parts.append(doc)

        parts.append("\n-# :x:  Failed")

        return '\n'.join(parts)
    


class GoofyAhhMomentError(UserReturnableError):
    """When something that should not be able to happen... happens."""
    
    def __str__(self):
        return textwrap.dedent("""
            A goofy-ahh-moment-exception has occurred!
            This means that nothing bad will result from it, but it still should definitely not have happened...
        """)
    

class SetupError(RuntimeError):
    """
    Raised when the setup process doesn't fully work.
    Critical, so it stops the process.
    """

    def __init__(self, *args):
        super().__init__(*args) 
    
    def __exception__(self, exc_type, exc_value, traceback):
        exit()


class CriticalError(RuntimeError):
    ...