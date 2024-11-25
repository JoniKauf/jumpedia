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



# --- Feedback Errors ---

class InvalidPermissionFeedbackError(FeedbackError):
    def __init__(self, ephemeral: bool = True):
        self.ephemeral = ephemeral

        super().__init__(
            error="Invalid Permission",
            details="You don't have valid permissions to use this command!",
            ephemeral=ephemeral
        )
    
class BadChannelFeedbackFeedbackError(FeedbackError):
    def __init__(self) -> None:
        super().__init__(
            error="Bad Channel",
            details="Command must be used in a channel where commands are allowed to be used!",
            ephemeral=True
        )

class InvalidAttributeFeedbackError(FeedbackError):
    def __init__(self, attr: str) -> None:
        self.attr = attr

        super().__init__(
            error="Invalid Attribute Error",
            details=f"The attribute `{attr}` is not valid!"
        )
        
class SameAttributeFeedbackError(FeedbackError):
    def __init__(self, attr: str, all_cases: Sequence[str] = ()):
        self.attr = attr
        self.all_cases = all_cases

        super().__init__(
            error="Same Attribute Error",
            details=f"The same attribute `{attr}` or synonyms of it were specified multiple times" +
            (
                "!" if not all_cases else
                ":\n" + msgt.shorten_and_embed_seq(all_cases)
            )
        )

class AttributeMissingFeedbackError(FeedbackError):
    def __init__(self, attrs: Sequence[str]):
        self.attrs = attrs

        super().__init__(
            error="Attribute Missing Error",
            details=f"The required attributes {msgt.shorten_and_embed_seq(attrs)} are missing!"
        )

class NotAJumpFeedbackError(FeedbackError):
    def __init__(self, jump_name: str):
        self.jump_name = jump_name
        
        super().__init__(
            error="Not A Jump",
            details=f"The jump `{jump_name}` doesn't exist in Jumpedia!"
        )

class JumpAlreadyObtainedFeedbackError(FeedbackError):
    def __init__(self, user_name: str):
        self.user_name = user_name

        super().__init__(
            error="Jump Already Obtained",
            details=f"The user `{user_name}` has already obtained that jump!"
        )

class JumpNotYetObtainedFeedbackError(FeedbackError):
    def __init__(self, user_name: str):
        self.user_name = user_name

        super().__init__(
            error="Jump Not Yet Obtained",
            details=f"The user `{user_name}` has not obtained that jump yet!"
        )

class NotAValidLinkFeedbackError(FeedbackError):
    def __init__(self, link: str):
        self.link = link

        super().__init__(
            error="Not A Valid Link",
            details=f"The link `{msgt.shorten(link)}` is not a valid URL!"
        )

class TooLongLinkFeedbackError(FeedbackError):
    def __init__(self, link: str, limit: int):
        self.link = link
        self.limit = limit

        super().__init__(
            error="Too Long Link",
            details=f"The link `{msgt.shorten(link)}` exceeds the maximum limit of `{limit}` characters!"
        )

class NoPermissionForOtherUsersFeedbackError(FeedbackError):
    def __init__(self):
        super().__init__(
            error="No Permission For Other Users",
            details="You do not have the required permissions to use this functionality for other users!"
        )

class NotAValidUserFeedbackError(FeedbackError):
    def __init__(self):
        super().__init__(
            error="Not A Valid User",
            details="The user specified is neither a valid user's ID nor a mention of a user."
        )

class UserNotFoundFeedbackError(FeedbackError):
    def __init__(self):
        super().__init__(
            error="User Not Found",
            details="The user specified could not be found!"
        )

class NoProofYetSetFeedbackError(FeedbackError):
    def __init__(self, user_name: str, jump_name: str):
        super().__init__(
            error="No Proof Yet Set",
            details=f"The user `{user_name}` has not set a proof for the jump `{jump_name}` yet!"
        )

class AllJumpsAndUserSpecifiedFeedbackError(FeedbackError):
    def __init__(self):
        super().__init__(
            error="All Jumps And User Specified",
            details="When selecting 'all' as the selection, you cannot specify a user!"
        )

class NoJumpFulfillingCriteriaFeedbackError(FeedbackError):
    def __init__(self):
        super().__init__(
            error="No Jump Fulfilling Criteria",
            details="There is no jump that fulfills both the criteria of the target and of the filter!"
        )

class OnCooldownFeedbackError(FeedbackError):
    def __init__(self, remaining: Real, action: str):
        self.remaining = remaining
        self.action = action

        super().__init__(
            error="On Cooldown",
            details=f"You have to wait another `{remaining:.1f}` seconds {action}!"
        )

class TooLongNameFeedbackError(FeedbackError):
    def __init__(self, name: str, max: int):
        self.name = name
        self.max = max

        super().__init__(
            error="Too Long Name",
            details=f"The entered name `{msgt.shorten(name)}` exceeds the limit of `{max}` characters!"
        )