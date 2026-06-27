from sqlalchemy import delete

from db.models import ServerModel
from domain.entities.community import CommunityEntity
from domain.types.server import ServerID
from repositories.base import BaseRepository


class ServerRepository(BaseRepository):
    def link(self, community: CommunityEntity, server_id: ServerID) -> None:
        self.session.add(
            ServerModel(
                server_id=server_id,
                community_id=community.community_id,
            )
        )
        self.session.flush()

    def unlink(self, server_id: ServerID) -> None:
        stmt = delete(ServerModel).where(ServerModel.server_id == server_id)
        self.session.execute(stmt)
        self.session.flush()
