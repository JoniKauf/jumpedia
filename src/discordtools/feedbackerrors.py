from discordtools import errors
from typing import Any, Optional as Opt, Sequence
from discordtools import msg as msgt
from numbers import Real

from structures import ranks

sh = msgt.shorten
spaced = lambda *s: ' '.join(s)

class InvalidPermission(errors.FeedbackError):
    def __init__(self, ephemeral: bool = True):
        self.ephemeral = ephemeral

        super().__init__(
            header="Invalid Permission",
            description="You don't have valid permissions to use this command!",
            ephemeral=ephemeral
        )

    
class BadChannel(errors.FeedbackError):
    def __init__(self) -> None:
        super().__init__(
            header="Bad Channel",
            description="Command must be used in a channel where commands are allowed to be used!",
            ephemeral=True
        )

class InvalidAttribute(errors.FeedbackError):
    def __init__(self, attr: str, expression: Opt[str] = None) -> None:
        self.attr = attr
        
        super().__init__(
            header="Invalid Attribute Error",
            description=(
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
            header="Invalid Sub Attribute",
            description=(
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
            header="Same Attribute Error",
            description=f"The same attribute `{attr}` or synonyms of it were specified multiple times!"
        )

class RequiredAttributesMissing(errors.FeedbackError):
    def __init__(self, attrs: Sequence[str]):
        self.attrs = attrs

        super().__init__(
            header="Attribute Missing Error",
            description=f"The required attributes {msgt.shorten_and_embed_seq(attrs)} are missing!"
        )

class NotAJump(errors.FeedbackError):
    def __init__(self, jump_name: str):
        self.jump_name = jump_name
        
        super().__init__(
            header="Not A Jump",
            description=f"The jump `{sh(jump_name)}` doesn't exist in Jumpedia!"
        )

class JumpAlreadyGotten(errors.FeedbackError):
    def __init__(self, user_name: Opt[str]):
        self.user_name = user_name

        super().__init__(
            header="Jump Already Gotten",
            description=(
                f"The user `{user_name}` has already gotten that jump!"
                if user_name is not None else 
                f"You have already gotten that jump!"
            )
        )

class JumpNotYetGotten(errors.FeedbackError):
    def __init__(self, user_name: Opt[str]):
        self.user_name = user_name

        super().__init__(
            header="Jump Not Yet Gotten",
            description=(
                f"The user `{user_name}` has not gotten that jump yet!"
                if user_name is not None else
                "You have not gotten that jump yet!"
            )
        )


class NoProofYetSet(errors.FeedbackError):
    def __init__(self, user_name: Opt[str]):
        super().__init__(
            header="No Proof Yet Set",
            description=(
                f"The user `{user_name}` has not set a proof for that jump yet!"
                if user_name is not None else
                "You have not set a proof for the jump that jump yet!"
            )
        )

class NotAValidLink(errors.FeedbackError):
    def __init__(self, link: str):
        self.link = link

        super().__init__(
            header="Not A Valid Link",
            description=f"The link `{sh(link)}` is not a valid URL!"
        )

class TooLongLink(errors.FeedbackError):
    def __init__(self, link: str, limit: int):
        self.link = link
        self.limit = limit

        super().__init__(
            header="Too Long Link",
            description=f"The link `{sh(link)}` exceeds the maximum limit of `{limit}` characters!"
        )

class NoPermissionForOtherUsers(errors.FeedbackError):
    def __init__(
        self, 
        user_rank_and_min: Opt[tuple[ranks.CommunityRank, ranks.CommunityRank]] = None, 
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
            header="No Permission For Other Users",
            description=spaced(
                "You do not have the required rank to use this",
                "functionality for other users in this context!",
                ("\n" + "\n".join(rank_addons)) if rank_addons else ""
            )
        )

class UserNotFound(errors.FeedbackError):
    def __init__(self):
        super().__init__(
            header="User Not Found",
            description="The user specified could not be found!"
        )

class AllJumpsAndUserSpecified(errors.FeedbackError):
    def __init__(self):
        super().__init__(
            header="All Jumps And User Specified",
            description="When selecting 'all' as the selection, you cannot specify a user!"
        )

class NoJumpFulfillingCriteria(errors.FeedbackError):
    def __init__(self):
        super().__init__(
            header="No Jump Fulfilling Criteria",
            description="There is no jump that fulfills both the criteria of the target and of the filter!"
        )

class OnCooldown(errors.FeedbackError):
    def __init__(self, remaining: Real, action: str):
        self.remaining = remaining
        self.action = action

        super().__init__(
            header="On Cooldown",
            description=f"You have to wait another `{remaining:.1f}` seconds {action}!"
        )

class TooLongName(errors.FeedbackError):
    def __init__(self, name: str, max: int):
        self.name = name
        self.max = max

        super().__init__(
            header="Too Long Name",
            description=f"The entered name `{sh(name)}` exceeds the limit of `{max}` characters!"
        )

class TooLongValue(errors.FeedbackError):
    def __init__(self, type: str, value: str, max: int):
        self.type = type
        self.name = value
        self.max = max

        super().__init__(
            header=f"Too Long {type.title()}",
            description=f"The entered {type.lower()} `{sh(value)}` (length: {len(value)}) exceeds the limit of `{max}` characters!"
        )

class PersonDoesNotExist(errors.FeedbackError):
    def __init__(self, person: str | int, say_user_instead: bool = False):
        convention: str = "user" if say_user_instead else "person"
        super().__init__(
            header=f"{convention.title()} Does Not Exist",
            description=f"The {convention} with the {"name" if isinstance(person, str) else "id"} `{person}` does not exist or could not be found!\nA person must have interacted with Jumpedia at least once before to become a user!"
        )

class InvalidSringFormat(errors.FeedbackError):
    def __init__(self, attr: str, wrong: str, right: str):
        super().__init__(
            header="Invalid String Format",
            description=f"For the attribute `{attr}` the value contained `{sh(wrong)}` which should be replaced by `{sh(right)}`!"
        )

class InvalidUserFormat(errors.FeedbackError):
    def __init__(self, id_format: int | str):
        super().__init__(
            header="Invalid User Format",
            description=f"The format `{sh(str(id_format))}` is not valid! Either mention the user with @username or enter their discord ID."
        )

class InternalDatabaseError(errors.FeedbackError):
    def __init__(self, inner: BaseException):
        self.inner = inner
        
        super().__init__(
            header="Internal Database Error",
            description=f"An internal database error occurred. This can happen, for example, when the data you tried to interact with got changed in that exact same moment.\nPlease try again and if the issue persists, try again later!"
        )

class NotAProperValue(errors.FeedbackError):
    def __init__(self, type: str, value: str):
        self.type = type
        self.value = value

        return super().__init__(
            header=f"Not A Proper {type.title()}",
            description=f"The specified string `{sh(value)}` is not a {type.lower()}!"
        )
    
class OutsideOfValidRange(errors.FeedbackError):
    def __init__[T](self, value: T, lb: T, ub: T):
        self.lb = lb
        self.ub = ub

        return super().__init__(
            header="Outside Of Valid Range",
            description=f"The value `{sh(str(value))}` is outside of the valid range reaching from `{lb}` to `{ub}`!"
        )


class NotAValidNumber(errors.FeedbackError):
    def __init__(self, n: int):
        self.n = n

        super().__init__(
            header="Not A Number",
            description=f"The specified number `{sh(str(n))}` is not valid in this context!"
        )

class NotPartOfTheCollection(errors.FeedbackError):
    def __init__(self, attr: str, value: str):
        self.attr = attr
        self.value = value

        super().__init__(
            header="Not Part Of The Collection",
            description=f"The value `{sh(value)}` is not a part of the attribute `{attr.lower()}` collection of valid values!"
        )


class CollectionElementCollision(errors.FeedbackError):
    def __init__(self, attr: str, value: str):
        self.attr = attr
        self.value = value

        super().__init__(
            header="Collection Element Collision",
            description=f"The collection of the attribute `{attr.lower()}` received the value `{sh(value)}` more than once (casing and extra whitespace is ignored)!"
        )

class TooManyCollectionElements(errors.FeedbackError):
    def __init__(self, attr: str, limit: int):
        self.attr = attr
        self.limit = limit

        super().__init__(
            header="Too Many Collection Elements",
            description=f"The collection of the attribute `{attr.lower()}` has a maximum limit of {limit} elements it can hold!"
        )

class InvalidValuesForDefiningAttribute(errors.FeedbackError):
    def __init__(self, attr: str, *values_name_typename: tuple[str, str]):
        self.attr = attr
        self.values_name_typename = values_name_typename

        super().__init__(
            header="Invalid Values For Defining Attribute",
            description=(
                f"For defining the attribute `{attr}` the following values and corresponding types are required:" +
                "".join(f"\n- **{name}**: *{typename}*" for name, typename in values_name_typename)
            )
        )


class TemporaryFeedbackError(errors.FeedbackError):
    def __init__(self, *args: Any):
        super().__init__(
            header="Temporary Feedback Error",
            description=(
                "This error is used as a placeholder and shouldn't occur outside of development. " +
                "If you see this, we are either still in development or Joni missed a spot.\n\n"
                "Debug info placeholder text that might be given:\n```" +
                ('\n'.join(f"- {arg}" for arg in args) if args else "<None>") +
                "\n```"
            )
        ) 