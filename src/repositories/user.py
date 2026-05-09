from db.models import User, CommunityUser
from domain.rank import CommunityRank, JumpediaRank
from utils import text
from .base import BaseRepository

class UserRepository(BaseRepository):
    def get_jumpedia_user(self, user_id: int) -> User | None:
        return self.session.get(User, user_id)
    
    def _create_user(self, user_id: int, norm_name: text.NormStr, raw_name: str, rank: JumpediaRank = JumpediaRank.DEFAULT) -> User:
        obj = User(
            user_id=user_id,
            raw_name=raw_name,
            norm_name=norm_name,
            power=rank,
        )

        self.session.add(obj)
        self.session.flush()

        return obj
    
    def _create_community_user(self, user_id: int, community_id: int, rank: CommunityRank = CommunityRank.DEFAULT, selected_list_id: int | None = None) -> CommunityUser:
        obj = CommunityUser(
            user_id=user_id,
            community_id=community_id,
            power=rank,
            selected_list_id=selected_list_id
        )

        self.session.add(obj)
        self.session.flush()

        return obj
    
    def create_user_and_community_user(
        self, 
        user_id: int, 
        norm_name: text.NormStr, 
        raw_name: str, 
        community_id: int, 
        jumpedia_rank: JumpediaRank = JumpediaRank.DEFAULT, community_rank: CommunityRank = CommunityRank.DEFAULT, selected_list_id: int | None = None) -> tuple[User, CommunityUser]:
        
        user = self._create_user(
            user_id=user_id,
            norm_name=norm_name,
            raw_name=raw_name,
            rank=jumpedia_rank
        )
        
        community_user = self._create_community_user(
            user_id=user_id,
            community_id=community_id,
            rank=community_rank,
            selected_list_id=selected_list_id
        )

        return user, community_user

    def get_community_user(self, community_user_id: int) -> CommunityUser | None:
        return self.session.get(CommunityUser, community_user_id)