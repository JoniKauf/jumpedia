from sqlalchemy import delete

from db.models import ServerModel
from domain.entities.community import CommunityEntity
from domain.typing.server import ServerID
from repositories.base import BaseRepository


class ServerRepository(BaseRepository):
    def link(self, community: CommunityEntity, server_id: ServerID) -> None:
        self._session.add(
            ServerModel(
                server_id=server_id,
                community_id=community.community_id,
            )
        )
        self._session.flush()

    def unlink(self, server_id: ServerID) -> None:
        stmt = delete(ServerModel).where(ServerModel.server_id == server_id)
        self._session.execute(stmt)
        self._session.flush()
