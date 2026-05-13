from dataclasses import asdict

from db.models import Community as Community, Server as ServerORM
from domain.value_objects import strings
from domain.value_objects.limits import Limits

from .base import BaseRepository
from utils import text

class CommunityRepository(BaseRepository):
    # -------------------------
    # CREATE
    # -------------------------
    def create(self, norm_name: strings.NormStr, real_name: strings.RealStr, limits: Limits) -> Community:
        obj = Community(
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
    def get_by_id(self, community_id: int) -> Community | None:
        return self.session.get(Community, community_id)

    def get_by_name(self, norm_name: strings.NormStr) -> Community | None:
        return (
            self.session.query(Community)
            .filter(Community.norm_name == norm_name)
            .first()
        )

    def get_all(self) -> list[Community]:
        return self.session.query(Community).all()

    # -------------------------
    # DELETE
    # -------------------------
    def delete(self, community_id: int) -> None:
        obj = self.get_by_id(community_id)

        if obj is not None:
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

    def get_by_server_id(self, server_id: int) -> Community | None:
        return (
            self.session.query(Community)
            .join(ServerORM, ServerORM.community_id == Community.community_id)
            .filter(ServerORM.server_id == server_id)
            .first()
        )

    def unlink_server(self, server_id: int) -> None:
        self.session.query(ServerORM).filter(
            ServerORM.server_id == server_id
        ).delete()