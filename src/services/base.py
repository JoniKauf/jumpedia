from domain.entities.community import CommunityEntity
from repositories.community import CommunityRepository
from db.models import Community
from domain import errors
from sqlalchemy.orm import Session

class BaseService:
    def __init__(self, session: Session) -> None:
        self.community_repo = CommunityRepository(session)

    def _get_community_by_server_id_or_throw(self, server_id: int) -> CommunityEntity:
        community = self.community_repo.get_by_server_id(server_id)

        if community is None:
            raise errors.NotInCommunity()
        
        return community