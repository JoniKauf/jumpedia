from repositories.list import ListRepository
from repositories.community import CommunityRepository
from domain.limits import Limits
from sqlalchemy.orm import Session

from utils import text

class ListService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.list_repo = ListRepository(session)
        self.community_repo = CommunityRepository(session)

    # -------------------------
    # CREATE LIST
    # -------------------------
    def create_list(self, community_id: int, name: str):
        real_name = text.RealStr(name)
        norm_name = text.NormStr(real_name)

        del name

        community = self.community_repo.get_by_id(community_id)

        if community is None:
            raise ValueError("community not found")

        existing_lists = self.list_repo.get_by_community(community_id)

        if len(existing_lists) >= community.limits:
            raise ValueError("list limit reached")

        if self.list_repo.get_by_name(community_id, norm_name):
            raise ValueError("list already exists")

        return self.list_repo.create(
            community_id=community_id,
            norm_name=norm_name,
            real_name=name,
        )

    # -------------------------
    # DELETE LIST
    # -------------------------
    def delete_list(self, community_id: int, list_id: int):
        lst = self.list_repo.get_by_id(list_id)
        if not lst or lst.community_id != community_id:
            raise ValueError("list not found")

        self.list_repo.delete(list_id)

    # -------------------------
    # RENAME LIST
    # -------------------------
    def rename_list(self, community_id: int, list_id: int, new_name: str):
        lst = self.list_repo.get_by_id(list_id)
        if not lst or lst.community_id != community_id:
            raise ValueError("list not found")

        norm_name = new_name.lower().strip()

        if self.list_repo.get_by_name(community_id, norm_name):
            raise ValueError("name already taken")

        lst.norm_name = norm_name
        lst.real_name = new_name