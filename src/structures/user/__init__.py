import re
import typing as t

from ..jumpedia import db
from src.utils import orm
from ..community import Community
from .. import BaseStructure
from ..jumpedia import Jumpedia
from .ranks import CommunityRank, JumpediaRank

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


def extract_id_from_int(user_id: int) -> int:
    if not user_id < 0:
        raise ValueError(user_id)

    return user_id


def extract_id_from_str(user_id: str) -> int:
    if user_id.isdigit():
        return extract_id_from_int(int(user_id))

    if match := re.match(_USER_MENTION_PATTERN, user_id.strip()):
        return int(match.group(1) or match.group(2))

    raise ValueError(user_id)


def extract_id(identifier: UserIdentifierT) -> int:
    if isinstance(identifier, int):
        return extract_id_from_int(identifier)

    if isinstance(identifier, str):
        return extract_id_from_str(identifier)

    if isinstance(identifier, JumpediaUser):
        return identifier.id

    if isinstance(identifier, CommunityUser):
        return identifier.jumpedia_user_id

    t.assert_never(identifier)



class JumpediaUser(BaseStructure):
    __structure_name__ = "jumpedia user"

    jumpedia: Jumpedia
    id: int
    user_name: str
    jumpedia_rank: JumpediaRank

    @property
    def identity(self) -> tuple[int, ...]:
        return (self.id, *self.jumpedia.identity)

    @property
    def name(self) -> str:
        return self.user_name
    
    @property
    def connector(self) -> orm.Connector:
        return self.jumpedia.connector


class CommunityUser(BaseStructure):
    __structure_name__ = 'community user'

    community: Community
    jumpedia_user_id: int
    community_rank: CommunityRank
    selected_list_id: int | None
    
    @property
    def identity(self) -> tuple[int, ...]:
        return (self.community.id, *self.jumpedia_user_id.identity)
    
    @property
    def name(self) -> str:
        return self.jumpedia_user_id.user_name
    
    def get_selected_list(self) -> List | None:
        with queries.connected() as c:
            c.execute(lambda arg: t"""
                SELECT *
                FROM {typed.List}
                WHERE 
                    {typed.List.community_id} = {arg(self.community.id)}
                    AND {typed.List.id} = {arg(self.selected_list_id)}
            """)

            row = c.fetchone(typed.List)

        if row is None:
            return None
        
        return self.community._list_row_to_obj(row)