


from dataclasses import dataclass
from typing import TYPE_CHECKING
from database import typed
from database import queries
from ranks.community_rank import CommunityRank
from structures import BaseStructure
from structures.user.jumpedia_user import JumpediaUser

if TYPE_CHECKING:
    from structures.community import Community
    from structures.list import List

class CommunityUser(BaseStructure):
    __structure_name__ = 'community user'

    community: Community
    jumpedia_user: JumpediaUser
    community_rank: CommunityRank
    selected_list_id: int | None
    
    @property
    def identity(self) -> tuple[int, ...]:
        return (self.community.id, *self.jumpedia_user.identity)
    
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