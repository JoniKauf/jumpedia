from typing import TYPE_CHECKING

from database import typed
from src.database import queries
from src.ranks.community_rank import CommunityRank
from src.ranks.jumpedia_rank import JumpediaRank
from src.structures import BaseStructure
from src.structures.user.community_user import CommunityUser
from structures import errors
from structures.community import Community

if TYPE_CHECKING:
    from ..jumpedia import Jumpedia




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