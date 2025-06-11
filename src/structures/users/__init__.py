

import re
from typing import Final, Sequence
import discord as dc

from discordtools.errors import FeedbackError
from structures.users.community_user import CommunityUser
from structures.users.meta_user import MetaUser
from structures.users.server_user import ServerUser

type AnyUserT = MetaUser | CommunityUser | ServerUser

type UserIdentifierT = int | str | AnyUserT | dc.User | dc.Member


MAX_SYN_LENGTH: Final[int] = 32
MAX_ALIAS_COUNT: Final[int] = 32

class InvalidUserFormat(FeedbackError):
    def __init__(self, user_format: str):
        return super().__init__(
            header="Invalid User Format", 
            description="The format `{}`"
        )

def extract_id_from_int(user_id: int) -> int:
    if user_id < 0:
        raise 
    
    return user_id

_USER_MENTION_PATTERN: re.Pattern = re.compile(r'^<@!?(\d+)>$|^<@&(\d+)>$')


def extract_id_from_str(user_id: str) -> int:
    if user_id.isdigit():
        return extract_id_from_int(int(user_id))

    if match := re.match(_USER_MENTION_PATTERN, user_id.strip()):
        return int(match.group(1) or match.group(2))
    
    raise fbe.InvalidUserFormat(user_id)


def extract_id(identifier: UserIdentifierT) -> int:
    if isinstance(identifier, int):
        return extract_id_from_int(identifier)
    
    if isinstance(identifier, str):
        return extract_id_from_str(identifier)
    
    if isinstance(identifier, CommunityUser | ServerUser):
        return identifier.meta_user.id

    if isinstance(identifier, MetaUser | dc.User | dc.Member):
        return identifier.id
    
    raise TypeError()


