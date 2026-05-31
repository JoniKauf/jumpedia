
from sqlalchemy import delete

from db.models import Server
from domain.entities.community import CommunityEntity
from domain.types.id import ID
from repositories.base import BaseRepository


class ServerRepository(BaseRepository):
    def link(self, community: CommunityEntity, server_id: ID) -> None:
        self.session.add(
            Server(
                server_id=server_id,
                community_id=community.id,
            )
        )
        self.session.flush()

    def unlink(self, server_id: ID) -> None:
        stmt = delete(Server).where(Server.server_id == server_id)
        self.session.execute(stmt)
        self.session.flush()