from sqlalchemy import delete

from jumpedia.db.models import ServerModel
from jumpedia.domain.entities.community import CommunityEntity
from jumpedia.domain.typing.server import ServerID
from jumpedia.repositories.base import BaseRepository


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
