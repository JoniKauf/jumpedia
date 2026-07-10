from dataclasses import dataclass

from domain.entities.community import CommunityEntity
from domain.enums.rank import ServerRank
from domain.errors import business
from domain.value_objects.community import CommunityNameStr
from repositories.community import CommunityRepository
from repositories.server import ServerRepository
from services.community import CommunityAccessService
from services.contexts.interacting_user import InteractingUserContext
from services.internal.permission import PermissionService


@dataclass(frozen=True, slots=True, eq=False)
class ServerService:
    _ctx: InteractingUserContext
    _server_repo: ServerRepository
    _community_repo: CommunityRepository
    _permission_service: PermissionService
    _community_access_service: CommunityAccessService

    def link(self, community_name: CommunityNameStr) -> CommunityEntity:
        self._permission_service.ensure_server_rank(
            required_server_rank=ServerRank.ADMINISTRATOR
        )

        community = self._community_repo.get_by_server_id(self._ctx.server_id)

        if community is not None:
            raise business.InCommunity(community)

        community = self._community_access_service.get_by_name_or_raise(community_name)

        self._server_repo.link(community, self._ctx.server_id)

        return community

    def unlink(self) -> CommunityEntity:
        self._permission_service.ensure_server_rank(
            required_server_rank=ServerRank.ADMINISTRATOR
        )

        community = self._community_access_service.get_current_or_raise()

        self._server_repo.unlink(self._ctx.server_id)

        return community
