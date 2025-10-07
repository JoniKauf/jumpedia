import typing as t
from dataclasses import dataclass

from ...database import queries, typed
from ...ranks.community_rank import CommunityRank
from .. import BaseStructure
from .jumpedia_user import JumpediaUser

if t.TYPE_CHECKING:
    from ..community import Community
    from ..list import List

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