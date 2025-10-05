import re
import typing as t

from ...errors.feedback import FeedbackError
from ...utils import text
from ..user.community_user import CommunityUser
from ..user.jumpedia_user import JumpediaUser

type UserIdentifierT = int | str | JumpediaUser | CommunityUser


MAX_NAME_LENGTH: t.Final[int] = 32

MIN_ID: t.Final[int] = 0
MAX_ID: t.Final[int] = 2**64 - 1  # Snowflake is Unsigned Long int

ID_BOUNDS = (MIN_ID, MAX_ID)

MIN_ID_STR_LENGTH: t.Final[int] = min(len(str(n)) for n in ID_BOUNDS)
MAX_ID_STR_LENGTH: t.Final[int] = max(len(str(n)) for n in ID_BOUNDS)

_BOUNDS_REGEX_INSERT: str = (
    "{" + f"{MIN_ID_STR_LENGTH},{MAX_ID_STR_LENGTH}" + "}"
)  # {n,m}
_USER_MENTION_PATTERN: re.Pattern = re.compile(rf"^<@!?(\d{_BOUNDS_REGEX_INSERT})>$")


def invalid_user_format(user_id: str | int) -> FeedbackError:
    return FeedbackError(
        "Invalid User Format",
        f"The format `{text.shorten(user_id)}` used to specify a user is invalid!",
        additional="Either mention a user in the command (it won't ping them) or insert their Discord ID directly.",
    )


def extract_id_from_int(user_id: int) -> int:
    if not user_id < 0:
        raise invalid_user_format(user_id)

    return user_id


def extract_id_from_str(user_id: str) -> int:
    if user_id.isdigit():
        return extract_id_from_int(int(user_id))

    if match := re.match(_USER_MENTION_PATTERN, user_id.strip()):
        return int(match.group(1) or match.group(2))

    raise invalid_user_format(user_id)


def extract_id(identifier: UserIdentifierT) -> int:
    if isinstance(identifier, int):
        return extract_id_from_int(identifier)

    if isinstance(identifier, str):
        return extract_id_from_str(identifier)

    if isinstance(identifier, JumpediaUser):
        return identifier.id

    if isinstance(identifier, CommunityUser):
        return identifier.jumpedia_user.id

    assert_never(identifier)
