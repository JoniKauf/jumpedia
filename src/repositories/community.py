from dataclasses import asdict

from db.models import Community as CommunityORM, Server as ServerORM
from domain.limits import Limits

from .base import BaseRepository
from utils import text

class CommunityRepository(BaseRepository):
    # -------------------------
    # CREATE
    # -------------------------
    def create(self, norm_name: text.NormStr, real_name: text.RealStr, limits: Limits) -> CommunityORM:
        obj = CommunityORM(
            norm_name=norm_name,
            real_name=real_name,
            **asdict(limits),
        )

        self.session.add(obj)
        self.session.flush()

        return obj

    # -------------------------
    # READ
    # -------------------------
    def get_by_id(self, community_id: int) -> CommunityORM | None:
        return self.session.get(CommunityORM, community_id)

    def get_by_name(self, norm_name: text.NormStr) -> CommunityORM | None:
        return (
            self.session.query(CommunityORM)
            .filter(CommunityORM.norm_name == norm_name)
            .first()
        )

    def get_all(self) -> list[CommunityORM]:
        return self.session.query(CommunityORM).all()

    # -------------------------
    # DELETE
    # -------------------------
    def delete(self, community_id: int) -> None:
        obj = self.get_by_id(community_id)
        if obj:
            self.session.delete(obj)

    # -------------------------
    # SERVER RELATIONSHIP
    # -------------------------
    def link_server(self, community_id: int, server_id: int) -> None:
        self.session.add(
            ServerORM(
                server_id=server_id,
                community_id=community_id,
            )
        )

    def get_by_server_id(self, server_id: int) -> CommunityORM | None:
        return (
            self.session.query(CommunityORM)
            .join(ServerORM, ServerORM.community_id == CommunityORM.community_id)
            .filter(ServerORM.server_id == server_id)
            .first()
        )

    def unlink_server(self, server_id: int) -> None:
        self.session.query(ServerORM).filter(
            ServerORM.server_id == server_id
        ).delete()