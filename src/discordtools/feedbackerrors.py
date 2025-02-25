from discordtools import errors
from typing import Optional as Opt, Sequence
from discordtools import messagetools as msgt
from numbers import Real

from people import ranks

sh = msgt.shorten
spaced = lambda *s: ' '.join(s)

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
    def __init__(self, attr: str, expression: Opt[str] = None) -> None:
        self.attr = attr
        
        super().__init__(
            error="Invalid Attribute Error",
            details=(
                f"The attribute `{sh(attr)}` is not valid!"
                if expression is None else
                f"The attribute `{sh(attr)}` from the expression `{sh(expression) or msgt.default_empty()}` is not valid in the given context!"
            )
        )

class InvalidSubAttribute(errors.FeedbackError):
    def __init__(self, attr: str, sub_attr: str, expression: Opt[str] = None):
        self.attr = attr
        self.sub_attr = sub_attr
        self.expression = expression

        super().__init__(
            error="Invalid Sub Attribute",
            details=(
                f"The attribute `{sh(attr)}` has no sub attribute `{sh(sub_attr)}`"
                + (
                    f" in the expression `{sh(expression) or msgt.default_empty()}`!"
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
            details=f"The jump `{sh(jump_name)}` doesn't exist in Jumpedia!"
        )

class JumpAlreadyGotten(errors.FeedbackError):
    def __init__(self, user_name: Opt[str]):
        self.user_name = user_name

        super().__init__(
            error="Jump Already Gotten",
            details=(
                f"The user `{user_name}` has already gotten that jump!"
                if user_name is not None else 
                f"You have already gotten that jump!"
            )
        )

class JumpNotYetGotten(errors.FeedbackError):
    def __init__(self, user_name: Opt[str]):
        self.user_name = user_name

        super().__init__(
            error="Jump Not Yet Gotten",
            details=(
                f"The user `{user_name}` has not gotten that jump yet!"
                if user_name is not None else
                "You have not gotten that jump yet!"
            )
        )


class NoProofYetSet(errors.FeedbackError):
    def __init__(self, user_name: Opt[str]):
        super().__init__(
            error="No Proof Yet Set",
            details=(
                f"The user `{user_name}` has not set a proof for that jump yet!"
                if user_name is not None else
                "You have not set a proof for the jump that jump yet!"
            )
        )

class NotAValidLink(errors.FeedbackError):
    def __init__(self, link: str):
        self.link = link

        super().__init__(
            error="Not A Valid Link",
            details=f"The link `{sh(link)}` is not a valid URL!"
        )

class TooLongLink(errors.FeedbackError):
    def __init__(self, link: str, limit: int):
        self.link = link
        self.limit = limit

        super().__init__(
            error="Too Long Link",
            details=f"The link `{sh(link)}` exceeds the maximum limit of `{limit}` characters!"
        )

class NoPermissionForOtherUsers(errors.FeedbackError):
    def __init__(
        self, 
        user_rank_and_min: Opt[tuple[ranks.UserRank, ranks.UserRank]] = None, 
        server_rank_and_min: Opt[tuple[ranks.ServerRank, ranks.ServerRank]] = None,
    ):
        self.user_rank_and_min = user_rank_and_min
        self.server_rank_and_min = server_rank_and_min
        
        rank_addons: list[str] = []
        
        if (
            user_rank_and_min and 
            user_rank_and_min[0] < user_rank_and_min[1]
        ):
            rank_addons.append(
                f"__Required User Rank__: `{user_rank_and_min[1]}`"
            )
        
        if (
            server_rank_and_min and 
            server_rank_and_min[0] < server_rank_and_min[1]
        ):
            rank_addons.append(
                f"__Required Server Rank:__ `{server_rank_and_min[1]}`"
            )

        if not rank_addons and (user_rank_and_min or server_rank_and_min):
            raise errors.ProgrammingError(
                "both ranks are high enough, so why even raise this feedback?"
            )
        
        super().__init__(
            error="No Permission For Other Users",
            details=spaced(
                "You do not have the required rank to use this",
                "functionality for other users in this context!",
                ("\n" + "\n".join(rank_addons)) if rank_addons else ""
            )
        )

class UserNotFound(errors.FeedbackError):
    def __init__(self):
        super().__init__(
            error="User Not Found",
            details="The user specified could not be found!"
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
            details=f"The entered name `{sh(name)}` exceeds the limit of `{max}` characters!"
        )

class TooLongValue(errors.FeedbackError):
    def __init__(self, value: str, max: int):
        self.name = value
        self.max = max

        super().__init__(
            error="Too Long Value",
            details=f"The entered value `{sh(value)}` (length: {len(value)}) exceeds the limit of `{max}` characters!"
        )

class PersonDoesNotExist(errors.FeedbackError):
    def __init__(self, person: str | int, say_user_instead: bool = False):
        convention: str = "user" if say_user_instead else "person"
        super().__init__(
            error=f"{convention.title()} Does Not Exist",
            details=f"The {convention} with the {"name" if isinstance(person, str) else "id"} `{person}` does not exist or could not be found!\nA person must have interacted with Jumpedia at least once before to become a user!"
        )

class InvalidSringFormat(errors.FeedbackError):
    def __init__(self, attr: str, wrong: str, right: str):
        super().__init__(
            error="Invalid String Format",
            details=f"For the attribute `{attr}` the value contained `{sh(wrong)}` which should be replaced by `{sh(right)}`!"
        )

class InvalidUserFormat(errors.FeedbackError):
    def __init__(self, id_format: int | str):
        super().__init__(
            error="Invalid User Format",
            details=f"The format `{sh(str(id_format))}` is not valid! Either mention the user with @username or enter their discord ID."
        )

class InternalDatabaseError(errors.FeedbackError):
    def __init__(self, inner: BaseException):
        self.inner = inner
        
        super().__init__(
            error="Internal Database Error",
            details=f"An internal database error occurred. This can happen, for example, when the data you tried to interact with got changed in that exact same moment.\nPlease try again and if the issue persists, try again later!"
        )

class NotANumber(errors.FeedbackError):
    def __init__(self, n: str):
        self.n = n

        super().__init__(
            error="Not A Number",
            details=f"The specified string `{sh(n)}` does not represent a number!"
        )

class NotAValidNumber(errors.FeedbackError):
    def __init__(self, n: int):
        self.n = n

        super().__init__(
            error="Not A Number",
            details=f"The specified number `{sh(str(n))}` is not valid in this context!"
        )