from discordtools import errors
from typing import Optional, Sequence
from discordtools import messagetools as msgt
from numbers import Real

short = msgt.shorten

class InvalidPermission(errors.FeedbackError):
    def __init__(self, ephemeral: bool = True):
        self.ephemeral = ephemeral

        super().__init__(
            error="Invalid Permission",
            details="You don't have valid permissions to use this command!",
            ephemeral=ephemeral
        )

    
class BadChannel(errors.FeedbackError):
    def __init__(self) -> None:
        super().__init__(
            error="Bad Channel",
            details="Command must be used in a channel where commands are allowed to be used!",
            ephemeral=True
        )

class InvalidAttribute(errors.FeedbackError):
    def __init__(self, attr: str, expression: Optional[str] = None) -> None:
        self.attr = attr
        
        super().__init__(
            error="Invalid Attribute Error",
            details=(
                f"The attribute `{short(attr)}` is not valid!"
                if expression is None else
                f"The attribute `{short(attr)}` from the expression `{short(expression) or msgt.default_empty()}` is not valid!"
            )
        )

class InvalidSubattribute(errors.FeedbackError):
    def __init__(self, attr: str, sub_attr: str, expression: Optional[str] = None):
        self.attr = attr
        self.sub_attr = sub_attr
        self.expression = expression

        super().__init__(
            error="Invalid Sub Attribute",
            details=(
                f"The attribute `{short(attr)}` has no subattribute `{short(sub_attr)}`"
                + (
                    f" in the expression `{short(expression) or msgt.default_empty()}`!"
                    if expression else "!"
                )
            )
        )

class SameAttribute(errors.FeedbackError):
    def __init__(self, attr: str):
        self.attr = attr

        super().__init__(
            error="Same Attribute Error",
            details=f"The same attribute `{attr}` or synonyms of it were specified multiple times!"
        )

class RequiredAttributesMissing(errors.FeedbackError):
    def __init__(self, attrs: Sequence[str]):
        self.attrs = attrs

        super().__init__(
            error="Attribute Missing Error",
            details=f"The required attributes {msgt.shorten_and_embed_seq(attrs)} are missing!"
        )

class NotAJump(errors.FeedbackError):
    def __init__(self, jump_name: str):
        self.jump_name = jump_name
        
        super().__init__(
            error="Not A Jump",
            details=f"The jump `{jump_name}` doesn't exist in Jumpedia!"
        )

class JumpAlreadyObtained(errors.FeedbackError):
    def __init__(self, user_name: str):
        self.user_name = user_name

        super().__init__(
            error="Jump Already Obtained",
            details=f"The user `{user_name}` has already obtained that jump!"
        )

class JumpNotYetObtained(errors.FeedbackError):
    def __init__(self, user_name: str):
        self.user_name = user_name

        super().__init__(
            error="Jump Not Yet Obtained",
            details=f"The user `{user_name}` has not obtained that jump yet!"
        )

class NotAValidLink(errors.FeedbackError):
    def __init__(self, link: str):
        self.link = link

        super().__init__(
            error="Not A Valid Link",
            details=f"The link `{msgt.shorten(link)}` is not a valid URL!"
        )

class TooLongLink(errors.FeedbackError):
    def __init__(self, link: str, limit: int):
        self.link = link
        self.limit = limit

        super().__init__(
            error="Too Long Link",
            details=f"The link `{msgt.shorten(link)}` exceeds the maximum limit of `{limit}` characters!"
        )

class NoPermissionForOtherUsers(errors.FeedbackError):
    def __init__(self):
        super().__init__(
            error="No Permission For Other Users",
            details="You do not have the required permissions to use this functionality for other users!"
        )

class NotAValidUser(errors.FeedbackError):
    def __init__(self):
        super().__init__(
            error="Not A Valid User",
            details="The user specified is neither a valid user's ID nor a mention of a user."
        )

class UserNotFound(errors.FeedbackError):
    def __init__(self):
        super().__init__(
            error="User Not Found",
            details="The user specified could not be found!"
        )

class NoProofYetSet(errors.FeedbackError):
    def __init__(self, user_name: str, jump_name: str):
        super().__init__(
            error="No Proof Yet Set",
            details=f"The user `{user_name}` has not set a proof for the jump `{jump_name}` yet!"
        )

class AllJumpsAndUserSpecified(errors.FeedbackError):
    def __init__(self):
        super().__init__(
            error="All Jumps And User Specified",
            details="When selecting 'all' as the selection, you cannot specify a user!"
        )

class NoJumpFulfillingCriteria(errors.FeedbackError):
    def __init__(self):
        super().__init__(
            error="No Jump Fulfilling Criteria",
            details="There is no jump that fulfills both the criteria of the target and of the filter!"
        )

class OnCooldown(errors.FeedbackError):
    def __init__(self, remaining: Real, action: str):
        self.remaining = remaining
        self.action = action

        super().__init__(
            error="On Cooldown",
            details=f"You have to wait another `{remaining:.1f}` seconds {action}!"
        )

class TooLongName(errors.FeedbackError):
    def __init__(self, name: str, max: int):
        self.name = name
        self.max = max

        super().__init__(
            error="Too Long Name",
            details=f"The entered name `{msgt.shorten(name)}` exceeds the limit of `{max}` characters!"
        )

class PersonDoesNotExist(errors.FeedbackError):
    def __init__(self, person: str | int):
        super().__init__(
            error="Person Does Not Exist",
            details=f"The person with the {"name" if isinstance(person, str) else "id"} `{person}` does not exist!"
        )

class InvalidSringFormat(errors.FeedbackError):
    def __init__(self, attr: str, wrong: str, right: str):
        super().__init__(
            error="Invalid String Format",
            details=f"For the attribute `{attr}` the value contained `{msgt.shorten(wrong)}` which should be replaced by `{msgt.shorten(right)}`!"
        )