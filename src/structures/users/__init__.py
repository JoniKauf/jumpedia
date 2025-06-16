

import re
from typing import Final, Never, Sequence
import discord as dc

from discordtools import messaging as msg
from errors.feedback import FeedbackError
from errors import ImpossibleError
from structures.users.community_user import CommunityUser
from structures.users.meta_user import MetaUser
from structures.users.server_user import ServerUser

type AnyUserT = MetaUser | CommunityUser | ServerUser

type UserIdentifierT = int | str | AnyUserT | dc.User | dc.Member


MAX_NAME_LENGTH: Final[int] = 32

MIN_ID: Final[int] = 0
MAX_ID: Final[int] = 2**64 - 1  # Snowflake is Unsigned Long int

ID_BOUNDS = (MIN_ID, MAX_ID)

MIN_ID_STR_LENGTH: Final[int] = min(len(str(n)) for n in ID_BOUNDS)
MAX_ID_STR_LENGTH: Final[int] = max(len(str(n)) for n in ID_BOUNDS)

_BOUNDS_REGEX_INSERT: str = "{" + f"{MIN_ID_STR_LENGTH},{MAX_ID_STR_LENGTH}" + "}" # {n,m}
_USER_MENTION_PATTERN: re.Pattern = re.compile(rf'^<@!?(\d{_BOUNDS_REGEX_INSERT})>$')

def _raise_invalid_user_format(user_id: str | int) -> Never:
    raise FeedbackError(
        "Invalid User Format",
        f"The format {msg.shorten_and_code(str(user_id))} used to specify a user is invalid!",
        additional="Either mention a user in the command (it won't ping them) or insert their Discord ID directly."
    )

def extract_id_from_int(user_id: int) -> int:
    if not user_id < 0:
        _raise_invalid_user_format(user_id)
    
    return user_id


def extract_id_from_str(user_id: str) -> int:
    if user_id.isdigit():
        return extract_id_from_int(int(user_id))

    if match := re.match(_USER_MENTION_PATTERN, user_id.strip()):
        return int(match.group(1) or match.group(2))
    
    raise _raise_invalid_user_format(user_id)


def extract_id(identifier: UserIdentifierT) -> int:
    if isinstance(identifier, int):
        return extract_id_from_int(identifier)
    
    if isinstance(identifier, str):
        return extract_id_from_str(identifier)
    
    if isinstance(identifier, CommunityUser | ServerUser):
        return identifier.meta_user.id

    if isinstance(identifier, MetaUser | dc.User | dc.Member):
        return identifier.id
    
    raise ImpossibleError()


