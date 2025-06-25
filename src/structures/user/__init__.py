

from dataclasses import dataclass
import re
from typing import Final, Never, Sequence
import discord as dc

from database import queries
from discordtools import messaging as msg
from errors.feedback import FeedbackError
from errors import ImpossibleError
from ranks.community_rank import CommunityRank
from ranks.jumpedia_rank import JumpediaRank
from ranks.server_rank import ServerRank
from structures.base_structure import BaseStructure
from structures.community import Community
from structures.jumpedia import Jumpedia
from database.typed import Tables as TBL
from database.typed import SingleTableRowT

type UserIdentifierT = int | str | User | dc.User | dc.Member


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
    
    if isinstance(identifier, User | dc.User | dc.Member):
        return identifier.id
    
    raise ImpossibleError()


@dataclass(frozen=True)
class User(BaseStructure):
    __structure_name__ = 'user'

    id: int
    name: str

    jumpedia: Jumpedia
    
    jumpedia_rank: JumpediaRank

    @property
    def identity(self) -> tuple[int, ...]:
        return (self.id,)

    def get_community_rank(self, community_id: int) -> CommunityRank | None:
        community = self.jumpedia.get_community_by_id(community_id)

        if community is None:
            return None
        
        h = queries.ArgHelper()

        with queries.connected() as (conn, cursor):
            cursor.execute(f"""
                SELECT {TBL.CommunityUser.power} 
                FROM {TBL.CommunityUser}
                WHERE 
                    {TBL.CommunityUser.community_id} = {h|community_id}
                    AND {TBL.CommunityUser.user_id} = {h|self.id}
            """)

            result: SingleTableRowT | None = cursor.fetchone()

        if result is None:
            return None
        
        return CommunityRank.get(result[TBL.CommunityUser.power])
    
    
    def get_server_rank(self, discord_user: dc.User | dc.Member) -> ServerRank | None:
        if isinstance(discord_user, dc.User):
            return None
        
        if discord_user.id == discord_user.guild.owner_id:
            return ServerRank.SERVER_OWNER
        
        if discord_user.guild_permissions.administrator:
            return ServerRank.SERVER_ADMINISTRATOR
        
        return ServerRank.MEMBER


    def most_important_rank_for_jumpedia(self, community_id: int) -> CommunityRank | JumpediaRank:
        return self.jumpedia_rank or self.get_community_rank(community_id) or JumpediaRank.NONE