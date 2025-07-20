


from dataclasses import dataclass
from database.typed import Tables as Tables
from database import typed
from database import queries
from ranks.community_rank import CommunityRank
from ranks.jumpedia_rank import JumpediaRank
from structures.base_structure import BaseStructure
from structures.community import Community
from structures.list import List
from structures.user.jumpedia_user import JumpediaUser


@dataclass(frozen=True, kw_only=True)
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
        h = queries.ArgHelper()

        with queries.connected() as (conn, cursor):
            cursor.execute(f"""
                SELECT *
                FROM {Tables.List}
                WHERE 
                    {Tables.List.community_id} = {h|self.community.id}
                    AND {Tables.List.id} = {h|self.selected_list_id}
            """, h.steal())

            result: typed.SingleTableRowT | None = cursor.fetchone()

        if result is None:
            return None
        
        return self.community._list_row_to_obj(result)