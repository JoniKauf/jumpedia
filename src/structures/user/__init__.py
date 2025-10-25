import re
import typing as t

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
        return identifier.jumpedia_user.id

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

    def get_or_create_community_user(
        self, 
        community_id: int,
        community_rank: CommunityRank, 
        selected_list_id: int | None, 
        override_community_rank_if_user_exists: bool,
        override_selected_list_if_user_exists: bool
    ) -> CommunityUser:
        with self.locked:
            community_user = self.get_community_user_by_id(self.id)
            
            with queries.connected() as c:
                # User doesn't exist yet
                if community_user is None:
                    c.execute(lambda arg: t"""
                        INSERT INTO {typed.CommunityUser} (
                            {typed.CommunityUser.community_id},
                            {typed.CommunityUser.jumpedia_user_id},
                            {typed.CommunityUser.power},
                            {typed.CommunityUser.selected_list_id}
                        )
                        VALUES (
                            {arg(community_id)},
                            {arg(self.id)},
                            {arg(community_rank.power)},
                            {arg(selected_list_id)}
                        )
                    """)

                else:
                    community_rank = community_rank if override_community_rank_if_user_exists else community_user.community_rank
                    selected_list_id = selected_list_id if override_selected_list_if_user_exists else community_user.selected_list_id

                    if community_rank != community_user or selected_list_id != selected_list_id:
                        c.execute(lambda arg: t"""
                            UPDATE {typed.CommunityUser}
                            SET 
                                {typed.CommunityUser.power} = {arg(community_rank.power)}
                                {typed.CommunityUser.selected_list_id} = {arg((None if selected_list_id is None else selected_list_id))}
                            WHERE 
                                {typed.CommunityUser.community_id} = {arg(community_id)}
                                AND {typed.CommunityUser.jumpedia_user_id} = {arg(self.id)}
                        """) 

            return CommunityUser(
                community=community_user.community,
                jumpedia_user=self,
                community_rank=community_rank,
                selected_list_id=selected_list_id
            )

    
    def get_community_user_by_id(self, community_id: int) -> CommunityUser | None:
        with queries.connected() as c:
            c.execute(lambda arg: t"""
                SELECT *
                FROM {typed.CommunityUser}
                WHERE 
                    {typed.CommunityUser.community_id} = {arg(community_id)}
                    AND {typed.CommunityUser.jumpedia_user_id} = {arg(self.id)}
            """)

            row = c.fetchone(typed.CommunityUser)
            
            community = self.jumpedia.get_community_by_id(community_id)

            if community is None:
                raise errors.StructureNotFoundError(Community)
            
        if row is None:
            return None
        
        return CommunityUser(
            community=community,
            jumpedia_user=self,
            community_rank=CommunityRank.get(row.power),
            selected_list_id=row.selected_list_id
        )
    


class CommunityUser(BaseStructure):
    __structure_name__ = 'community user'

    community: Community
    jumpedia_user: JumpediaUser
    community_rank: CommunityRank
    selected_list_id: int | None
    
    @property
    def identity(self) -> tuple[int, ...]:
        return (self.community.id, *self.jumpedia_user.identity)
    
    @property
    def name(self) -> str:
        return self.jumpedia_user.user_name
    
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